---
name: shard
description: 背景委派 — 把需求切進獨立 worktree 丟給背景 worker,做完自動收回主線。非同步做事用這個;同步第二意見用 /kimi /codex。
argument-hint: "[需求]   |   --keep [需求]   |   [需求 A] ; [需求 B] ..."
allowed-tools: Task, Agent, Bash, Read, Edit, Write, SendMessage
disable-model-invocation: true
---

把以下需求切成獨立 worktree 丟給**背景 worker**(subagent_type=worker)去做,**主 session 不要自己動手**做這塊。這套系統的存在理由:取代「同一個 project 開 2-3 個對話窗」——所以**同 repo 多 shard 並行是常態**,收尾規則(land.md)都為此設計。

需求:$ARGUMENTS

## 兩種模式(看 `$ARGUMENTS` 開頭旗標)
- **預設(無旗標)= Mode A 一次性**:射出 → 自己做完 → **完成通知進來自動 land** → 消失。適合邊界清楚的小塊。
- **`--keep`(或 `--iterate`)= Mode B 持久迭代**:射出 → 做完一個單元就回報、**不自動 land** → 可反覆追加需求 → Howard 說「land <id>」才收。適合會長出來的探索性需求。

## Manifest 是真相來源
點火時落檔 `~/.claude/shards/<agentId>.json`;收尾/迭代**從這檔讀**,不靠對話脈絡——脈絡會被壓縮或記錯。Schema(`*` 必填,射出時就要有):

```json
{
  "agentId": "*最新一個 worker 的 id",
  "agentHistory": ["歷任 agentId,含最新"],
  "repo": "*", "baseBranch": "*", "baseCommit": "*",
  "task": "*一句需求", "mode": "*oneshot | keep",
  "status": "*fired | iterating | landing | resolving | blocked | conflict | pr-open",
  "createdAt": "*ISO UTC", "updatedAt": "*ISO UTC(每次狀態變更都更新)",
  "worktreePath": "完成通知後補", "worktreeBranch": "完成通知後補",
  "lastCommit": "完成通知後補",
  "prUrl": "pr 策略才有",
  "stagedFollowup": { "commit": "", "desc": "", "pushed": false, "gate": "等什麼外部條件" }
}
```
- 時間戳用 `date -u +%Y-%m-%dT%H:%M:%SZ`。
- land 策略**不存 manifest**——唯一權威是 `~/.claude/shards/policy.json`,land 當下讀。

## A. 射出去(現在)
1. **確認落點是 git repo**:`git rev-parse --show-toplevel` → `REPO`。失敗(例如在 `~/Projects` 母目錄)→ 不要射,告訴 Howard 要在哪個專案裡跑並停。
2. **記錄基準點**:`BASE=$(git branch --show-current)`、`COMMIT=$(git rev-parse HEAD)`。
3. **同 repo 已有 shard 在飛?** 掃 `~/.claude/shards/*.json` 同 `repo` 且 status 非 pr-open 的:若新需求跟在飛的**範圍明顯重疊**(動同一批檔案),合成一個 shard 或建議排序做,回報一句原因;不重疊就照常並行。
4. **點火**:把「`REPO` + `BASE` + 當前對話窗在做什麼」塞進 worker prompt。多個需求用 `;` 分隔 → 各開一個並行;每個拿到自己的 `agentId`。
5. **落檔 manifest**(每個 worker 一份,含 `createdAt`/`updatedAt`/`agentHistory`)。
6. **立刻還 Howard 控制權**:只回每個 worker 的 id + 一句需求 + mode。**不要等、不要貼 worker 輸出。**

## 完成通知 / land / 迭代 / 棄置
一律照 `~/.claude/skills/shard/land.md` 做——那裡有完整收尾流程、**自動決策表**(什麼自動做、什麼才准打斷 Howard)、per-repo land lock、push 節流(防 Railway 連環部署)。
