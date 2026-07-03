#!/usr/bin/env python3
"""shard 狀態板 + reality-check;--gc 加三向對帳。唯讀:只印報告,絕不刪東西。"""
import datetime
import glob
import json
import os
import subprocess
import sys

SHARDS_DIR = os.path.expanduser("~/.claude/shards")
POLICY_FILE = os.path.join(SHARDS_DIR, "policy.json")
STALE_DAYS = 3


def sh(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 1, str(e)


def age_days(m, path):
    ts = m.get("updatedAt") or m.get("createdAt")
    if ts:
        try:
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() / 86400
        except ValueError:
            pass
    return (datetime.datetime.now().timestamp() - os.path.getmtime(path)) / 86400


def branch_exists(repo, branch):
    if not (repo and branch and os.path.isdir(repo)):
        return None
    code, _ = sh(["git", "-C", repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
    return code == 0


def check(m):
    """回 (ok, [問題])。只驗 manifest 有記錄的東西。"""
    problems = []
    wp = m.get("worktreePath")
    if wp and not os.path.isdir(wp):
        problems.append("worktree遺失")
    wb = m.get("worktreeBranch")
    be = branch_exists(m.get("repo"), wb)
    if wb and be is False:
        problems.append("branch遺失")
    if m.get("repo") and not os.path.isdir(m["repo"]):
        problems.append("repo遺失")
    return (not problems, problems)


def load_manifests():
    out = []
    for f in sorted(glob.glob(os.path.join(SHARDS_DIR, "*.json"))):
        if os.path.basename(f) == "policy.json":
            continue
        try:
            m = json.load(open(f))
        except Exception as e:
            print(f"⚠ 壞掉的 manifest {os.path.basename(f)}: {e}")
            continue
        out.append((f, m))
    return out


def board(manifests):
    if not manifests:
        print("目前沒有在飛的 shard。")
        return
    print(f"{'id':17} {'mode':8} {'status':10} {'age':>5} {'repo':20} {'base':10} {'check':22} task")
    print("-" * 118)
    gated = []
    for f, m in manifests:
        rid = (m.get("agentId") or os.path.basename(f).replace(".json", ""))[:16]
        repo = os.path.basename(m.get("repo", "?"))[:19]
        days = age_days(m, f)
        age = f"{days:.0f}d" if days >= 1 else f"{days * 24:.0f}h"
        ok, problems = check(m)
        status = m.get("status", "?")
        zombie = (not ok) and status in ("iterating", "blocked", "conflict", "fired", "resolving")
        chk = "ok" if ok else "⚠" + ("殭屍:" if zombie and days >= STALE_DAYS else "") + ",".join(problems)
        print(f"{rid:17} {m.get('mode','?'):8} {status:10} {age:>5} {repo:20} {m.get('baseBranch','?'):10} {chk[:22]:22} {m.get('task','')[:40]}")
        sf = m.get("stagedFollowup") or {}
        if sf.get("gate") and not sf.get("pushed"):
            gated.append((rid, sf))
    if gated:
        print("\n等外部條件(stagedFollowup):")
        for rid, sf in gated:
            print(f"  {rid}: commit {sf.get('commit','?')} — {sf.get('desc','')} | gate: {sf['gate']}")


def gc(manifests):
    print("\n═══ GC 三向對帳(唯讀報告,不會動任何東西)═══")
    # (a) 殭屍 manifest
    zombies = [(f, m) for f, m in manifests if not check(m)[0]]
    print(f"\n(a) 殭屍 manifest({len(zombies)}):")
    for f, m in zombies:
        print(f"  rm {f}   # {', '.join(check(m)[1])}; task: {m.get('task','')[:50]}")
        sf = m.get("stagedFollowup") or {}
        if sf.get("gate") and not sf.get("pushed"):
            print(f"    ⚠ 內含未完成 stagedFollowup(commit {sf.get('commit')}, gate: {sf['gate']})——刪前先確認這筆是否還要")
    if not zombies:
        print("  無")

    # repo 清單:manifests + policy registry
    repos = {m.get("repo") for _, m in manifests if m.get("repo")}
    if os.path.exists(POLICY_FILE):
        try:
            repos |= set(json.load(open(POLICY_FILE)).get("repos", {}).keys())
        except Exception as e:
            print(f"⚠ policy.json 讀不了: {e}")
    repos = sorted(r for r in repos if r and os.path.isdir(r))
    tracked_wp = {m.get("worktreePath") for _, m in manifests if m.get("worktreePath")}

    # (b) 無主 worktree
    print("\n(b) 無主 worktree(有 worktree、無 manifest):")
    found_b = False
    for repo in repos:
        code, out = sh(["git", "-C", repo, "worktree", "list", "--porcelain"])
        if code != 0:
            continue
        for block in out.split("\n\n"):
            lines = dict(l.split(" ", 1) for l in block.splitlines() if " " in l)
            wp = lines.get("worktree")
            if not wp or os.path.realpath(wp) == os.path.realpath(repo):
                continue  # 主 working copy 不算
            if "/.claude/worktrees/" not in wp:
                continue  # 只管 harness/shard 開的
            if wp in tracked_wp:
                continue
            found_b = True
            days = (datetime.datetime.now().timestamp() - os.path.getmtime(wp)) / 86400 if os.path.isdir(wp) else -1
            print(f"  git -C {repo} worktree remove {wp}   # {days:.0f}d 舊, branch {lines.get('branch','?').replace('refs/heads/','')}")
    if not found_b:
        print("  無")

    # (c) worktree-agent-* 殘枝
    print("\n(c) worktree-agent-* 殘枝:")
    found_c = False
    for repo in repos:
        code, out = sh(["git", "-C", repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/worktree-agent-*"])
        if code != 0 or not out:
            continue
        code2, base = sh(["git", "-C", repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        base = base.replace("origin/", "") if code2 == 0 else "main"
        _, merged = sh(["git", "-C", repo, "branch", "--merged", base, "--format=%(refname:short)"])
        merged_set = set(merged.splitlines())
        for br in out.splitlines():
            found_c = True
            if br in merged_set:
                print(f"  git -C {repo} branch -d {br}   # 已合入 {base},安全刪")
            else:
                print(f"  ⚠ {repo} 的 {br} 未合入 {base} —— 刪要 -D(撞 git-guard),交 Howard 決定")
    if not found_c:
        print("  無")


def main():
    manifests = load_manifests()
    board(manifests)
    if "--gc" in sys.argv:
        gc(manifests)


if __name__ == "__main__":
    main()
