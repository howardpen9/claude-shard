# claude-shard

<p align="center">
  <img src="docs/assets/hero.png" alt="claude-shard — 隔離 git worktree 裡的並行 Claude Code worker" width="100%" />
</p>

**Claude Code skill：** 在隔離的 git worktree 裡跑並行 worker — 射出、落地、結束。

> **主要受眾：** 你以 **Claude Code** 當主 coding agent（一個視窗當 driver）。  
> 這**不是** Grok plugin、不是 MCP、不是 peer-review slash。它是架在 Claude 原生 `Agent` + `isolation: worktree` + background 之上的 **Claude Code skill + agent**。

English: [README.md](./README.md)

---

## 什麼時候值得裝

以下**大多成立**再裝：

1. **Claude Code 是你的主入口** — 日常活在一個（或少數幾個）Claude session，不是多 CLI peer slash。
2. 你常在**同一個 repo 開 2–3 個 Claude 視窗**，彼此踩同一批檔、互相搞混。
3. 希望主 session 當 **dispatcher + integrator** — 用指令**強制**切分，而不是祈禱模型「會自己用 subagent」。
4. 收工要的是 **可合併的 git 單元**，不是貼回一段文字：rebase → 測試 → merge 或 PR。
5. 同 repo **接了部署**（Railway / Vercel / push-to-deploy），**每次 push 可能等於一次 deploy** — 需要 **push 節流**，避免並行 shard 連環部署。

**別裝**，改用 Claude 內建就好：

| 你只要… | 改用 stock Claude Code |
| --- | --- |
| 短並行探索 / 分析 | 同一則訊息多個 `Agent` call |
| 對話分叉（兩邊各自繼續） | `/fork`（背景 session 副本） |
| 大規模機械改檔 → **每單位一個 PR** | 內建 **`/batch`** |
| 同步第二意見（Codex / Kimi） | Peer / MCP — **不是** `/shard` |

Claude 本來就有 worktree、背景 agent、`/tasks`、`/batch`。  
**Shard 不取代它們。** 補的是你工作流還缺的：**你強制切分**、**disk manifest 當真相來源**、**auto land 規則**、**同 repo land lock**、**deploy-safe 批次 push**。

<p align="center">
  <img src="docs/assets/before-after.png" alt="之前：三個 Claude 視窗互踩 — 之後：/shard 並行 worktree" width="100%" />
</p>

---

## 你得到什麼（僅 Claude Code）

| 指令 | 做什麼 |
| --- | --- |
| `/shard <任務>` | **Mode A（一次性）：** 射出 → worker 做完 → 完成通知 **自動 land** → 結束 |
| `/shard --keep <任務>` | **Mode B（迭代）：** 每做完一個單元回報、不 land；可一直追加；說 `land <id>` 才合 |
| `/shard A ; B ; C` | 多任務並行 — 一個需求一個 worker |
| `/shards` | 狀態板：在飛 / 卡住 / 可追加（worktree、branch 是否還在、年齡、殭屍旗標） |
| `/shards --gc` | 三向對帳：殭屍 manifest / 無主 worktree / 殘留 `worktree-agent-*` 分支（唯讀報告） |

<p align="center">
  <img src="docs/assets/commands.png" alt="指令速查" width="100%" />
</p>

**不是 peer review：** `/kimi`、`/codex` 是**同步**第二意見。`/shard` 是**非同步**背景**實作** + git land。

---

## 安裝（Claude Code）

```sh
git clone https://github.com/howardpen9/claude-shard.git
cd claude-shard
./install.sh   # symlink skills + agent → ~/.claude，建立 ~/.claude/shards/
```

然後**開一個新的 Claude Code session**（skill 在 session 啟動時載入）。

- 這個目錄是源頭；`~/.claude/skills/shard` 等是 symlink。
- 執行期狀態在 `~/.claude/shards/`（manifest、`policy.json`、locks）— 不進 git。

**Monorepo dogfood（ops workspace）：** 若你在 `coding-agent-mcps` 裡開發，改從那邊裝：

```sh
cd /path/to/coding-agent-mcps/claude-shard && ./install.sh
```

---

## 為什麼不只用 stock Claude Code？

Claude Code 已有 subagent（`Agent` + `background` + `isolation: worktree`）、`/tasks`、`/fork`、`/batch`。Shard **不重寫 runtime** — 補的是**使用者強制切分**，以及 git **落地最後一哩**。

| | `/tasks`（內建） | 裸 subagent（內建） | `/batch`（內建） | `/shard` |
| --- | --- | --- | --- | --- |
| 誰發起切分 | 模型自己記帳 | 你描述派工；模型決定 | Skill 拆 5–30 單位 | **你強制：** `/shard A ; B ; C` — 主 session 不准自己做這塊 |
| 工作單位 | 一行描述 | 一個 agent、文字回覆 | worktree + **每單位一 PR** | worktree + branch + **manifest** = 可合併單元 |
| 做完之後 | 核取方塊 | 貼結果；合併靠臨場 | 開 draft PR | **Auto land：** rebase → 測試 → 依 policy merge **或** PR |
| 狀態壽命 | 當前 session | agent 結束就沒 | Session / PR URL | **Disk manifest**；隨時 `/shards` |
| 部署意識 | 無 | 無 | 無 | Policy registry + **push 節流**（「push = 一次 deploy」） |

內建是**被動零件** — 每次派工要靠 prompt 勸、每次回來要臨場合併。Shard 把它們變成**主動動詞**：切分是指令，land 是規則表。一個 Claude Code 視窗就能當 dispatcher + integrator。

---

## 怎麼運作

<p align="center">
  <img src="docs/assets/flow.png" alt="射出 → 工作 → land → deploy-safe" width="100%" />
</p>

### 1. Manifest 是真相來源

每個 shard 寫入 `~/.claude/shards/<agentId>.json`（repo、base、mode、status、時間戳、agentHistory）。Land / 迭代**讀檔**，不靠聊天脈絡 — 脈絡會被壓縮、記錯。Schema：`skills/shard/SKILL.md`。

### 2. Land 決策表（敘述句，不問句）

「有沒有衝突？」「要不要合併？」預設**不打斷你**。自動處理：rebase 衝突（在 worktree 內解；大衝突開 resolve-worker）、測試紅（fix-worker 修一次）、工作區髒（試 fast-forward）。只在三類情況打斷：新 repo 第一次選 land policy、會觸發 deploy 的 push/merge（整批問一次）、guard 擋下 / 刪未合併工作。完整表：`skills/shard/land.md`。

### 3. 同 repo 並行安全（切斷 deploy 連環）

- **Per-repo land lock**（`mkdir` 原子）：兩個 session 不會同時 land 同一個 repo
- **在 worktree 內 rebase**：worker 可接手解衝突；也修 harness worktree 釘死在 session 起點 snapshot 的問題（`rebase --onto`）
- **Push 節流**：同 repo 還有 shard 在飛 → 只本地 merge、先不 push；全部做完再批次問一次 = 一次 deploy

### 4. Per-repo land 策略 registry

`~/.claude/shards/policy.json`：`local-merge | merge-no-push | pr`。新 repo 第一次 land 會偵測 deploy 訊號（Railway / Vercel / workflows）→ 建議策略、問一次、寫回 registry。`pr` **絕不**本地合 main（避免接部署的 repo 誤觸 deploy）。

---

## 目錄結構

```
skills/shard/SKILL.md            # /shard 射出流程 + manifest schema
skills/shard/land.md             # land：決策表、lock、rebase、push 節流、迭代/棄置
skills/shards/SKILL.md           # /shards 看板 + 詮釋規則
skills/shards/scripts/board.py   # reality-check + --gc 對帳（唯讀）
agents/worker.md                 # 背景 worker（isolation: worktree + background: true）
install.sh                       # symlink 進 ~/.claude
docs/assets/                     # README 概念圖
MONOREPO.md                      # coding-agent-mcps workspace 說明（若有）
```

---

## Harness 坑（為什麼要有 land 邏輯）

1. **Stale worktree base：** harness worktree 釘在 session 起點 → 直接 `merge --ff-only` 會失敗；用 `git rebase --onto BASE $(git merge-base BASE WB) WB`。
2. **git-guard hook：** `branch -D` / `reset --hard` 被擋；自動流程**絕不**夾帶 `#guard-ok`。Worker 固定一條分支 → merge 後可用安全的 `branch -d`。
3. **Stale `index.lock`：** rebase 完立刻 `switch`/`merge` 會撞鎖；land 步驟分開跑；撞到鎖先 `pgrep -fl git` 再重試。

---

## Backlog

- Mode B 跨 session 復活（SendMessage 失敗 → 從 `worktreeBranch` 重射）尚未 live-test
- 完整 `pr` push+PR 路徑尚未在真 repo live-test
- resolve-worker / fix-worker 路徑尚未實戰驗證
- 自動偵測 land 後 verify 指令；大 diff 自動掛 `/code-review` gate

---

## 在 Claude Code 以外的參考價值

即使你的主 agent 是 Grok Build / Codex / Cursor：

- **Manifest-as-SoT**、**land 決策表**、**push 節流** 對任何 worktree 並行設定都可重用。
- Grok 的 `/fork --worktree` / `spawn_subagent(isolation: worktree)` 涵蓋「拆出去」原語；**沒有**這層 land / policy。
- 在 **coding-agent-mcps** monorepo 裡，這個資料夾當「dispatcher + integrator」的 **ops 範例** — 見 monorepo `docs/PLAYBOOK.md`、`AGENTS.md`。

---

## Keywords

Claude Code, git worktree, parallel agents, background subagent, multi-agent workflow, auto land, deploy-safe merge, Railway push throttle, agent orchestration, dispatcher pattern
