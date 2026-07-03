---
name: shards
description: shard 狀態板 — 列出在飛/卡住/可追加的背景委派,含 reality-check(worktree/branch 是否還在、年齡)與 --gc 三向對帳。唯讀。
argument-hint: "[--gc]"
allowed-tools: Bash, Read
disable-model-invocation: true
---

跑板子腳本(唯讀,不刪任何東西):

```bash
python3 ~/.claude/skills/shards/scripts/board.py $ARGUMENTS
```

腳本自己做 reality-check:每個 manifest 驗 worktree 路徑、branch 是否還在,顯示年齡,標 `⚠` 過期項;`--gc` 加印三向對帳(殭屍 manifest / 無主 worktree / worktree-agent-* 殘枝)。

印完用一兩句**固定格式**詮釋,不要展開細節:
- `in flight: N | iterating: N | 卡住: N | 等外部條件: N`
- 卡住的(`blocked`/`conflict`):一句說卡在哪,提醒可「land <id>」「丟掉 <id>」或給指示。
- `iterating`:提醒可直接追加需求(SendMessage 原 agent,叫不回會自動重新點火——見 shard/land.md C 段)。
- `iterating`/`blocked` 超過 3 天且 reality-check 已標 `⚠`:直接說「疑似殭屍,建議 gc」。
- `stagedFollowup.gate` 有值的:單獨一句列「在等什麼」。

`--gc` 時:把腳本列出的清理候選整理成清單給 Howard 過目,**他點頭才動手**(殭屍 manifest 用 `rm`;無主 worktree 用 `git worktree remove`;已合併殘枝 `git branch -d`;未合併的要 `-D` 會撞 git-guard → 交 Howard 帶 token 執行)。

這只是看板;真正的 land / 迭代 / 棄置動作走 `~/.claude/skills/shard/land.md` 的流程。
