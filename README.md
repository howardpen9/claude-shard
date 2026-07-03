# claude-shard

把需求切給**背景 worktree-隔離 worker**、跑完自動收回主線的 Claude Code 工作流。

**存在理由:取代「同一個 project 開 2-3 個 Claude Code 對話窗」。** 多開 session 會互相衝突(工作區互踩、各自 push 觸發連環部署);shard 把並行搬進 git worktree,收尾統一由主 session 按規則辦。

## 指令

| 指令 | 作用 |
|---|---|
| `/shard <需求>` | Mode A 一次性:射出 → worker 做完 → 完成通知進來**自動 land** → 消失 |
| `/shard --keep <需求>` | Mode B 持久迭代:做完一單元回報不 land,可反覆追加,說「land \<id\>」才收 |
| `/shard A ; B ; C` | 多需求並行,各開一個 worker |
| `/shards` | 狀態板:在飛 / 卡住 / 可追加,含 reality-check(worktree/branch 還在嗎、年齡、殭屍標記) |
| `/shards --gc` | 三向對帳:殭屍 manifest / 無主 worktree / `worktree-agent-*` 殘枝(唯讀報告) |

定位區分:`/kimi` `/codex` = 同步第二意見;`/shard` = 非同步背景委派。

## 設計核心

### 1. Manifest 是真相來源
每個 shard 落檔 `~/.claude/shards/<agentId>.json`(repo、base、mode、status、時間戳、agentHistory)。收尾/迭代**從檔案讀**,不靠對話脈絡——脈絡會被壓縮或記錯。schema 見 `skills/shard/SKILL.md`。

### 2. Land 自動決策表(敘述句回報,不問句打斷)
「有沒有衝突」「要不要合併」永遠不問人。自動處理:rebase 衝突(worktree 內解,大的點火 resolve-worker)、測試紅(fix-worker 修一次)、髒工作區(直接試 ff)。只有三類事准打斷:新 repo 首次選 land 策略、會觸發部署的 push/合 PR(批次問一次)、guard 擋下/刪未合併工作。全表見 `skills/shard/land.md`。

### 3. 同 repo 並行三防線(防 Railway 連環部署)
- **per-repo land lock**(`mkdir` 原子性):兩個 session 不會同時收同一個 repo
- **rebase 在 worktree 內跑**:worker 才接得手解衝突;也解掉 harness worktree 釘在 session 快照、落後主線的問題(`rebase --onto`)
- **push 節流**:同 repo 還有 shard 在飛 → 只合本地、hold push;全收完批次問一次 = 一次部署

### 4. Per-repo land 策略 registry
`~/.claude/shards/policy.json`:`local-merge | merge-no-push | pr`。新 repo 第一次 land 偵測 deploy 訊號(railway/vercel/workflow)→ 建議策略、問一次、記回。`pr` 策略絕不本地合主線(deploy-connected repo 防誤部署)。

## 檔案

```
skills/shard/SKILL.md     # /shard 射出流程 + manifest schema
skills/shard/land.md      # 收尾:決策表、lock、rebase、push 節流、迭代/棄置、鐵律
skills/shards/SKILL.md    # /shards 板子 + 詮釋規則
skills/shards/scripts/board.py   # reality-check + --gc 對帳(唯讀)
agents/worker.md          # 背景 worker(isolation: worktree + background: true)
install.sh                # symlink 進 ~/.claude
```

執行期狀態(**不進 repo**,住 `~/.claude/shards/`):manifests、`policy.json`、`locks/`、GC log。

## 安裝

```sh
./install.sh   # symlink skills + agent 進 ~/.claude,建 ~/.claude/shards/
```

repo 是唯一源頭;`~/.claude` 只放 symlink,改 repo 即生效(新 skill 需下個 session 載入)。

## Harness 暗坑(收尾邏輯為此而生)

1. **worktree 起點落後**:harness worktree 釘在 session 起點快照 → 天真 `merge --ff-only` 必失敗;正解 `git rebase --onto BASE $(git merge-base BASE WB) WB`。
2. **git-guard hook**:`branch -D`/`reset --hard` 被擋;自動流程**絕不自帶 `#guard-ok` 繞過**,停下問人。worker 不另開分支 → 合併後 `branch -d` 安全刪,天然避開。
3. **index.lock 殘鎖**:rebase 剛結束緊接 `switch`/`merge` 會撞鎖;收尾各步分開跑,撞到先 `pgrep -fl git` 確認再重試。

## Backlog

- Mode B 跨 session 復活路徑(SendMessage 失敗 → 從 worktreeBranch 重新點火)未 live-test
- `pr` 策略完整 push+PR 路徑未對真 repo live-test
- resolve-worker / fix-worker 路徑未實戰
- land 後驗證命令自動偵測;大改自動接 /code-review gate
