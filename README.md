# claude-shard

<p align="center">
  <img src="docs/assets/hero.png" alt="claude-shard — parallel workers in isolated git worktrees" width="100%" />
</p>

**Parallel Claude Code workers in isolated git worktrees — fire, land, done.**

Replace “open 2–3 Claude Code windows on the same project.” Multiple sessions stomp the same workspace and each push can trigger a deploy storm. Shard moves parallelism into **git worktrees**; the main session only dispatches and integrates.

<p align="center">
  <img src="docs/assets/before-after.png" alt="Before: 3 Claude windows conflict — After: /shard parallel worktrees" width="100%" />
</p>

## Commands

| Command | What it does |
|---|---|
| `/shard <task>` | **Mode A (oneshot):** fire → worker finishes → completion notice **auto-lands** → gone |
| `/shard --keep <task>` | **Mode B (iterate):** report after each unit, no land; append freely; say `land <id>` to integrate |
| `/shard A ; B ; C` | Parallel tasks — one worker per demand |
| `/shards` | Status board: in-flight / stuck / open for follow-up (reality-check: worktree/branch alive?, age, zombie flags) |
| `/shards --gc` | Three-way reconcile: zombie manifests / orphan worktrees / leftover `worktree-agent-*` branches (read-only report) |

<p align="center">
  <img src="docs/assets/commands.png" alt="Command cheat sheet" width="100%" />
</p>

**Not the same as second-opinion peers:** `/kimi` and `/codex` are **sync** review. `/shard` is **async** background delegation.

## Why not stock Claude Code?

Claude Code already has subagents (`Agent` + `background` + `isolation: worktree`) and `/tasks`. Shard does not reimplement them — it adds what is missing: **forced split by the user** and the **last mile of git landing**.

| | `/tasks` (built-in) | Raw subagent (built-in) | `/shard` |
|---|---|---|---|
| Who initiates the split | Model bookkeeping | You describe dispatch in the prompt; model decides | **You force the split:** `/shard A ; B ; C` — main session must not do the work |
| Work unit | One-line description | One agent, text reply | worktree + branch + manifest = **mergeable unit** |
| After finish | Checkbox | Paste result; merge is ad hoc | **Auto land:** rebase → tests → merge or open PR per policy; one-line report |
| State lifetime | In-session | Dies with the agent | Manifest on disk; survives session/context compression; `/shards` anytime |
| Deploy awareness | None | None | Policy registry + push throttle (“push = one Railway deploy”) |

Built-ins are **passive parts** — every dispatch needs prompt persuasion and every return needs improvised merge. Shard makes them **active verbs**: split is a command, land is a ruleset. The main session becomes **dispatcher + integrator**, so one window can act like two or three.

## How it works

<p align="center">
  <img src="docs/assets/flow.png" alt="fire → work → land → deploy-safe" width="100%" />
</p>

## Design core

### 1. Manifest is source of truth

Each shard writes `~/.claude/shards/<agentId>.json` (repo, base, mode, status, timestamps, agentHistory). Land and iterate **read the file**, not chat context — context gets compressed and forgotten. Schema: `skills/shard/SKILL.md`.

### 2. Land decision table (statements, not questions)

“Is there a conflict?” and “should we merge?” never interrupt you by default. Automatic: rebase conflicts (resolve in worktree; large ones spawn a resolve-worker), red tests (one fix-worker pass), dirty tree (try fast-forward). Only three interrupt classes: first land-policy pick for a new repo, push/merge that would deploy (one batch ask), guard block / delete unmerged work. Full table: `skills/shard/land.md`.

### 3. Same-repo parallel safety (stop Railway deploy chains)

- **Per-repo land lock** (`mkdir` atomic): two sessions never land the same repo at once
- **Rebase inside the worktree**: workers can resolve conflicts; also fixes harness worktrees pinned to a stale session snapshot (`rebase --onto`)
- **Push throttle**: if the same repo still has shards in flight → merge locally only, hold push; when all are done, batch-ask once = one deploy

### 4. Per-repo land policy registry

`~/.claude/shards/policy.json`: `local-merge | merge-no-push | pr`. First land on a new repo detects deploy signals (Railway / Vercel / workflows) → suggests a policy, asks once, stores it. `pr` never merges to main locally (avoids accidental deploys on deploy-connected repos).

## Layout

```
skills/shard/SKILL.md            # /shard fire flow + manifest schema
skills/shard/land.md             # land: decision table, lock, rebase, push throttle, iterate/discard, hard rules
skills/shards/SKILL.md           # /shards board + interpretation rules
skills/shards/scripts/board.py   # reality-check + --gc reconcile (read-only)
agents/worker.md                 # background worker (isolation: worktree + background: true)
install.sh                       # symlink into ~/.claude
docs/assets/                     # README concept art (hero / before-after / flow / commands)
```

Runtime state (**not in the repo**, lives under `~/.claude/shards/`): manifests, `policy.json`, `locks/`, GC log.

## Install

```sh
./install.sh   # symlink skills + agent into ~/.claude, create ~/.claude/shards/
```

This repo is the source of truth; `~/.claude` only gets symlinks. Edit here and it applies (new skills need a new session to load).

## Harness gotchas (why land logic exists)

1. **Stale worktree base:** harness worktrees pin to the session start snapshot → naive `merge --ff-only` fails; use `git rebase --onto BASE $(git merge-base BASE WB) WB`.
2. **git-guard hook:** `branch -D` / `reset --hard` blocked; auto flows **never** smuggle `#guard-ok`. Workers stay on one branch → safe `branch -d` after merge.
3. **Stale `index.lock`:** rebase then immediate `switch`/`merge` races the lock; land steps run separately; on lock, `pgrep -fl git` then retry.

## Backlog

- Mode B cross-session revive (SendMessage fail → re-fire from `worktreeBranch`) not live-tested
- Full `pr` push+PR path not live-tested on a real repo
- resolve-worker / fix-worker paths not battle-tested
- Auto-detect post-land verify commands; large diffs auto-attach `/code-review` gate

## Keywords

Claude Code, git worktree, parallel agents, background subagent, multi-agent workflow, auto land, deploy-safe merge, Railway push throttle, agent orchestration, dispatcher pattern
