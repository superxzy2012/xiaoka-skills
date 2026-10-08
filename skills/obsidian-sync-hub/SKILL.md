---
name: obsidian-sync-hub
description: 把 NAS vault 目录同步到 GitHub 枢纽仓库 obsidian-sync。
---

# Obsidian 枢纽同步（obsidian-sync）

触发：需要把 vault 目录推到 GitHub 枢纽、跑 `dy_sync.sh`、或排查同步误删时。

## 仓库事实（别再重新发现）
- 远端 `git@github.com:superxzy2012/obsidian-sync.git` 是**私有**仓库，main 分支。
- 远端内容 = **整个 vault**（约 6700 文件），不是只有某个子目录。
- 远端 `SYNC.md` 规定：方向双向，push 前先 `pull --rebase`。以它为准。
- NAS 本地 vault 只有部分内容，远端有本地**没有**的文件（Mac/Cloud 节点写的）。
  实测 2026-10-07：08 目录远端 1294 vs 本地 1028，526 个仅远端有。
- 远端笔记 frontmatter 用 `aweme_id`，本地 `ingest.py` 生成的用 `douyin_id`，
  两边 id 交集很小（325 vs 244，交集仅 6），**别用 id 数当文件数**。

## 脚本
`/opt/data/sync/dy_sync.sh`（cron `30fba1cdedfa`，每日 17:30 触发）

| 参数 | 行为 |
|---|---|
| 无参数 | dry-run，报告变更后回滚，不提交不推送 |
| `--push` | 真同步 |
| `--reclone` | 丢弃工作副本重新 clone（副本损坏时） |

退出码：`0` 正常 / `2` rebase 冲突（已中止，未推送）/ `3` clone 或 push 失败 /
`4` stage 含删除（安全闸拦下）/ `5` 另一个实例正在运行。

## 🔴 三个必须记住的坑

### 1. 绝不能用「复制本地 + git add -A + push」
本地是远端子集，`add -A` 会把远端独有文件全 stage 成删除，一次推送就毁掉几百篇笔记。
正解：**clone 远端 → 只覆盖本地要同步的目录 → 只 add 那一个路径**。
只 add 单路径 = 其他目录的删除永远不会被 stage。

### 2. `pull --rebase` 必须在 overlay 之前
`git pull --rebase` 要求工作树**完全干净**，有任何 staged/unstaged 改动直接报错退出：
```
error: cannot pull with rebase: You have unstaged changes.
```
若把 overlay（复制本地文件）放在 pull 前，每次必失败。而且这段非零退出很容易被
误判成「rebase 冲突」，报错信息完全误导人。
正确顺序：`reset → pull → overlay → add → 安全闸 → commit → push`。

### 3. clone 绝不能并发
两个 git 进程同时 clone 同一目录会写坏 `.git/objects/pack`：
```
fatal: could not open '.../tmp_pack_xxx' for reading: No such file or directory
fatal: fetch-pack: invalid index-pack output
```
cron 和手动跑撞车就会中招，留下半截坏仓库。脚本已加 `flock`（exit 5 挡住）。

## 其它要点
- 工作副本放 `/opt/data/sync/obsidian-sync`（本地 SSD），**绝不放 NAS 磁盘**——
  NAS 磁盘 checkout 极慢（2.3MB 要 180s）。
- 大二进制（`*.mp4` 等）vault 的 `.gitignore` 已排除，但 **PNG 帧图会进 git**。
  只同步单个目录，别把 vault 根的 `attachments/`（992MB）拖进去。
- deploy key：`/opt/data/.ssh/obsidian-sync`（600），公钥副本在
  `/opt/data/sync/DEPLOY_KEY.pub.txt`。脚本已显式 export `GIT_SSH_COMMAND`，
  否则 ssh 只用默认 `id_ed25519`（那是给 Windows 用的，GitHub 不认）。
- 交付任何公钥前自检：`grep '^ssh-ed25519' 文件 | ssh-keygen -lf -` 与
  `ssh-keygen -lf 私钥` 指纹必须一致。
- 同名文件内容冲突时**本地优先**：NAS 上的笔记经 factcheck / dy_author_fix
  校对过（例：author 已从 uid 修成真名），远端是未校对版本。
- 推送后**必须回源验证**，别只信退出码：`git ls-remote` 看远端 HEAD 是否等于
  本地 commit，再数远端文件总数确认无意外删除。

## 汇报纪律
推送失败就说失败，贴错误原文和单步下一步。不要写「已同步」这种没有回执的话。