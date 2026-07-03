# shard 收尾:完成通知 → land / 迭代 / 棄置

## 自動決策表(最高原則:敘述句回報,不問句打斷)

「有沒有衝突」「要不要合併」這類問題**永遠不問 Howard**——要嘛自動處理,要嘛落板批次。只有表裡標「是」的三類事才准打斷:

| 情境 | 動作 | 打斷? |
|---|---|---|
| rebase 乾淨 / 測試綠 | 直接續 land | 否 |
| rebase 衝突 | 在 worktree 內解:≤3 檔的小衝突主 session 自解;更大 → 點火 resolve-worker(status=`resolving`),它解完通知進來自動重進 land;解不掉 → status=`conflict` 落板 | 否 |
| 測試紅 | 點火 fix-worker 修一次;再紅 → status=`blocked` 落板 | 否 |
| BASE 工作區髒 | 直接試 ff-merge(git 只擋真重疊的檔);被擋 → status=`blocked` 落板 | 否 |
| policy 已登記 | 照做不問 | 否 |
| policy 未登記(新 repo) | 偵測 deploy 訊號 → 建議一個,問一次,答案記回 `policy.json` | **是**(僅首次) |
| push 會觸發部署 / 合 PR | hold,同 repo 全收完批次問一次 | **是**(批次) |
| git-guard 擋下 / 棄置未合併工作 | 停 | **是** |

落板 = 更新 manifest status + `updatedAt`,回 Howard 一句敘述(不是問句),細節留給 `/shards`。

## B. 完成通知進來時
通知有 `task-id`(=agentId)、`worktreePath`(WP)、`worktreeBranch`(WB)。

0. 讀 manifest `~/.claude/shards/<task-id>.json` → `REPO`、`BASE`、`mode`;把 WP/WB/lastCommit 補進 manifest。manifest 不在 → 用通知資訊 + 問 Howard 確認 base,**別猜**(這是少數准問的:沒有真相來源)。
1. worker 回報有 blocker → status=`blocked` 落板,停。
2. `mode=keep` → **不 land**。status=`iterating`,回一句「shard <id> 完成單元:<摘要>」,worktree 留著。
3. `mode=oneshot` → 往下自動 land。
4. status=`resolving` 的通知(= resolve/fix worker 回來)→ 成功就從 Land 第 3 步續走;失敗 status=`conflict`/`blocked` 落板。

## Land(Mode A 自動;或 Howard 說「land <id>」)

> 同 repo 多 shard 並行是常態,所以:**lock 串行化 + 在 worktree 內 rebase + push 節流**。

1. **搶 lock**:`mkdir ~/.claude/shards/locks/<repo-slug>`(slug = repo 路徑 `/`→`-`)。失敗:lock 目錄 mtime < 30 分鐘 → 另一個 session 在收這個 repo,status 不動、回一句「<repo> 正被收尾,稍後自動重試」,下次通知/被叫再試;≥ 30 分鐘 → 殘鎖,`rmdir` 後重搶。**拿到 lock 後 status=`landing`;此後任何提前退出(含落板)都要先 `rmdir` 釋放。**
2. `MB=$(git merge-base BASE WB)`、`own=$(git rev-list $MB..WB --count)`;`own=0` → 無變更:remove worktree、刪 manifest、釋放 lock,回報「無變更」。
3. **在 WP 內 rebase**(WB 在那裡 checked out,worker 才接得了手):`git -C WP rebase --onto BASE $MB WB`。衝突 → 按決策表(自解 / resolve-worker / 落板;落板前 `git -C WP rebase --abort`)。
4. **在 WP 跑測試 / build**(rebase 後的程式碼才是要 land 的);紅 → 按決策表。
5. `git diff BASE...WB` review:正確性 + 有無夾帶不該動的檔。真可疑(夾帶 secret、動到無關子系統)才落板,不然續走。
6. **讀策略**:`~/.claude/shards/policy.json` 的 `repos[<REPO>]`(唯一權威,manifest 裡的舊 `landPolicy` 一律無視)。未登記 → 偵測 deploy 訊號(`railway.json`/`railway.toml`/`vercel.json`/`nixpacks.toml`/`Procfile`/deploy workflow)→ 有建議 `pr`、無建議 `local-merge`,**問一次**,記回 registry。
7. `git worktree remove WP --force`(rebase 已完成,worktree 可放)。
8. **按策略結案**(各步分開跑,別擠 `&&` 鏈——rebase 剛完 index.lock 可能未釋放):
   - **`local-merge` / `merge-no-push`**:`git switch BASE` → `git merge --ff-only WB` → `git branch -d WB`(已合,安全刪)→ 刪 manifest。**一律不 push**;若 repo 有 deploy 訊號,把「BASE 領先 origin N commits」記著,等該 repo 沒有在飛的 shard 時**批次問一次**要不要 push(= 部署一次)。
   - **`pr`**:**絕不本地合 BASE**。`git push -u origin WB` → `gh pr create --base BASE --head WB --fill` → status=`pr-open` + `prUrl`,manifest 不刪、本地 WB 不刪。推分支不觸發部署可直接推;但**合 PR 會**——回報時提示「等同 repo 其他 shard 的 PR 一起 review 再合,免連環部署」。
9. **釋放 lock**(`rmdir`)。
10. **回報固定格式一行**:`landed <id>: <n> commits, tests <pass|fail>, policy <x>`(pr 策略則 `pr-open <id>: <prUrl>, tests <pass|fail>`;hold push 時加 `, push held (N in flight)`)。

## C. 迭代 / 手動 land / 棄置(Mode B)
- **追加需求**:先 `SendMessage`(to = manifest `agentId`)——背景 agent 跨 session 存活,通常叫得回。**叫不回**(送失敗/無回應)→ fallback:從 manifest 的 `worktreeBranch` 重新點火新 worker(worktree 還在就叫它在 WP 裡做;不在就先 `git worktree add WP WB` 重建),新 id 推進 `agentHistory`、`agentId` 指向它。這整段自動做,不用問。
- **手動 land**:Howard 說「land <id>」→ 走上面 Land 整套。
- **棄置**:Howard 說「丟掉 <id>」→ 這是刪未合併工作,**確認一次**再 `git worktree remove WP --force`;分支未合需 `-D` 會撞 guard → 交 Howard 帶 token 執行;若 status=pr-open 提醒關 PR。刪 manifest。

## 鐵律
- 被 `git-guard` 擋下,**不自帶 `#guard-ok` 繞過,停下問 Howard**。
- push / 合 PR / 任何會觸發部署的動作,只走決策表「批次問」那一行,絕不順手做。
- 不確定 base 且 manifest 不在 → 問,別猜;其餘按決策表,**能自動就自動,能落板就不即時打斷**。
- 收尾各步分開跑;撞 `.git/index.lock` 先 `pgrep -fl git` 確認無真 git 程序,是陳留鎖就刪掉重試,別當致命錯。
