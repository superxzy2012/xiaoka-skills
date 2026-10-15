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
`4` stage 含删除（安全闸拦下）/ `5` 另一个实例正在运行 / `6` commit 失败（多为 git 身份缺失）。

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

### 4. 静默假成功三连（2026-10-15 实测，最危险）
三个 bug 叠起来会输出「已提交 + 已是最新，跳过 push」，看起来完全成功，实际零推送：
1. 工作副本 `.git/config` 里的 `user.name/email` 丢了（重建/换手就会丢）→
   `git commit` 直接 `fatal: unable to auto-detect email address`。
2. 脚本没有 `set -e`，commit 失败后继续跑，还打出「已提交: <上一次的 commit>」。
3. `if git push origin main | sed ...; then` —— `if` 取的是管道**最后一条**(sed)的退出码，
   推送失败照样打 `PUSH_OK`。
规则：① git 身份每次运行都设（不能只放在 clone 分支里）；② `if ! git commit ...` 失败即 exit 6；
③ push 用 `git push >log 2>&1; RC=$?` 取真实退出码；④ **推送后必须回源**：
`git ls-remote <repo> refs/heads/main` 的 sha 要等于本地 `rev-parse HEAD`。

### 5. 本机不可读的 vault 文件会让整轮同步中止
vault 08 目录里有 25 个 `-rw------- superxzy` 的文件（BOSS 自己账号建的），
hermes 读不到 → `cp -a` 返回非零 → 被误判「覆盖失败」整轮 exit 1。
正解：overlay 改用 `tar -C src -cf - --ignore-failed-read . | tar -C dst -xf -`，
然后**逐个核对**每个不可读文件在工作副本里已存在（存在才敢跳过，因为本地是远端子集）；
有任何缺失就 exit 1，绝不静默继续。

### 6. `.hermes-tmp.XXXXXX` 残留会被提交进仓库
写文件工具的草稿残留在 NAS 08 目录里（内容是被替换前的旧版笔记），`add -A` 会把它当新笔记推上去。
`add` 必须带排除：
```bash
git add -A -- "$SCOPE" ":(exclude)$SCOPE/.hermes-tmp.*" ":(exclude)$SCOPE/**/.hermes-tmp.*"
```
🔴 这些残留**小卡自己删不掉**（见下节写权限），要请 BOSS 用他自己的账号清。

## 从枢纽读别人交付的东西（只读，不动工作树）

云端 / 其它节点的 agent 把交付物提交进这个仓库后，取件用 fetch + `git show`，**不要 checkout**：

```bash
cd /opt/data/sync/obsidian-sync
GIT_SSH_COMMAND="ssh -i /opt/data/.ssh/obsidian-sync -o IdentitiesOnly=yes" git fetch origin
git show <commit>:<path> > /tmp/out.md                  # 内容到手，工作树不动
git log -1 --format='%H%n%an%n%ad%n%s' <commit>          # 谁、什么时候提交的
```

- **`gh api` 看不到这个私库**：`gh auth status` 显示已登录，但
  `gh api repos/superxzy2012/obsidian-sync/...` 一律 404（token 对该私库无权限）。取件走 deploy key，
  别在这上面绕。
- fetch 回来的 commit **可能不挂在任何远程分支上**（`git branch -r --contains <sha>` 为空）——
  只要能 `git show` 出内容就够用，不必为了「找到分支」继续折腾。
- **数 md 篇数必须 `-z`**：中文/空格路径被 git 加引号转义，`grep -c '\.md$'` 会少算一个数量级。
  同一仓库实测 `29` vs `4980`：

```bash
git ls-files -z | tr '\0' '\n' | grep -cE '\.md$'
```

## 其它要点
- 🔴 **小卡对 vault 只有读权限，写不进去**（2026-10-15 实测）：`08-抖音视频学习/` 是
  `drwxr-xr-x superxzy:admin`，hermes(uid 10000) 和 `ssh DY`(uid 1005) 都 `test -w` = no、
  实际写入 `[Errno 13] Permission denied`。目录里 243 个 hermes 属主文件是**早期**写的。
  结论：新笔记「落 NAS」这一步需要 BOSS 放开权限（把 hermes 加进属主组 / 给 ACL rwx / chmod 777）
  或给一条免密写路径；在此之前 `ingest.py` 会在 `shutil.copy` 到 NAS 时失败。
  排查手法：`test -w <dir>` 只能看模式位，**真写一次**才算数。
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

## Gitea 内网枢纽（NAS 自建，2026-10-01 建）

同一份 vault 在 NAS 上还有第二个 Git 枢纽：**自建 Gitea**，属于 10-01 那次「Mac / NAS / 腾讯云(101.35.95.101) 三方同步」方案的中枢。跟 GitHub 那条链路是两套东西，别混。

| 项 | 值 |
|---|---|
| Web / HTTP git | `http://192.168.199.2:3000`（内网 8ms）；Gitea 1.27.3 |
| SSH git | `ssh://git@192.168.199.2:2222/anc/obsidian.git` |
| 容器 / compose | `gitea`（`gitea/gitea:1`）；`/home/DY/gitea/docker-compose.yml` |
| 数据（NAS 宿主） | `/home/DY/gitea/data`（`DY` 可读；宿主**无 git 命令**，git 操作走容器） |
| 用户 / 仓库 | 只有 `anc`（admin，注册已关 `DISABLE_REGISTRATION=true`）／只有 `anc/obsidian`（**private**） |
| 内容 | 整个 vault 基线：6451 文件 / 2.3GB（pack 1.4GB；大文件全在 `12-知识星球` 的 PDF/PPT/PNG，最大 15.8MB） |
| 凭据 | NAS `/home/DY/gitea_admin.env`（600，`GITEA_URL/ADMIN/PASS/TOKEN`）——**只给路径，绝不回显** |

**取用（已验证）**：小卡容器可直连 HTTP+token，匿名一律 401（private 生效）：

```bash
# token 从 NAS 读进环境变量，用 GIT_ASKPASS 喂 git，避免 URL 里出现明文
GITEA_PW=$(ssh -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 'grep "^GITEA_TOKEN=" /home/DY/gitea_admin.env | cut -d= -f2-')
GIT_ASKPASS=<临时脚本: echo "$GITEA_PW"> git ls-remote http://anc@192.168.199.2:3000/anc/obsidian.git
```

- SSH 方式目前**只注册了 Mac 贾维斯那把 key**（`mac-jarvis-nas-tm`，`SHA256:ddagrH53Zu72Ip8bjWF3xrmVFj9cEEe2MVQFmhvqNL4`）；本机 `id_ed25519` 未注册 → `Permission denied (publickey)`。要用 SSH 得先在 Web UI 或 API 加公钥。
- 排障：`sudo -n docker exec -u git gitea git --git-dir=/data/git/repositories/anc/obsidian.git log --oneline`；Web 访问记录 `sudo -n docker logs gitea | grep HTTPRequest`；SSH 记录 `grep -iE "Accepted publickey|preauth"`。
- 现状（2026-10-15 核实）：最后 push `2026-10-01 11:23`；Mac(`.119`) 最后一次 git 操作 `2026-10-09`；之后只有 BOSS 的 Windows(`.184`) 手动开过 Web 首页。主同步链路已换成 GitHub `superxzy2012/obsidian-sync`。

### Gitea 镜像（2026-10-15 接上，BOSS 令：多一层内网备份）

| 项 | 值 |
|---|---|
| 脚本 | `/opt/data/sync/gitea_mirror.sh`（`--check` 只比对两边 sha） |
| cron | job `b6bffe27b607`，expr `30 18 * * *`（**UTC**，= 北京 02:30，在 dy_sync 之后 1 小时） |
| 做法 | `git push gitea refs/remotes/origin/main:refs/heads/main` —— 直推 remote-tracking ref，**不碰工作树**：工作树脏（dy_sync 的 overlay 残留）不影响它，也不可能 stage 删除 |
| 锁 | 与 dy_sync.sh **共享** `/tmp/dy_sync.lock`（同一工作副本，并发 git 会写坏 pack）；撞锁 exit 5 |
| 安全闸 | 只允许 fast-forward；gitea 若有 GitHub 没有的提交 → exit 1，**绝不 force push** |
| 认证 | `/opt/data/.ssh/gitea-mirror`（600），公钥已注册到 gitea 的 `anc` 账号（title `xiaoka-hermes-nas-mirror`，指纹 `SHA256:k4XU6/aNe3kNH0mIKL1G8BufJ75G2u8DyIkL4qjMius`）；加 key 走 `POST /api/v1/user/keys` |
| 退出码 | `0` 成功（含「已是最新」）/ `1` 失败 / `5` 撞锁 |

首次镜像实测：`87042e3..d9fae82` fast-forward，1.7 秒，311 对象 / 4.6MB，回源 sha 一致。

🔴 **已知缺口**：镜像的是 **GitHub 枢纽的内容**，而枢纽里**没有** NAS 本地独有目录 ——
`15-小卡工作区`(8523 文件)、`OZON`(663)、`00-Business_Layer_OZON`、`01-Research_Layer_AI_Factory`、`08-抖音`。
这些既不在 GitHub 也不在 Gitea，**目前无任何远端备份**。要给它们上备份得另开一条推送（注意 dy_sync 的 `add -A` 会误删远端独有文件，必须只 add 单路径）。

计数（必须 `-z`，中文路径被 git 加引号转义）：枢纽 6721 文件 / 4996 md / `08-抖音视频学习` 1425 md。

## 汇报纪律
推送失败就说失败，贴错误原文和单步下一步。不要写「已同步」这种没有回执的话。