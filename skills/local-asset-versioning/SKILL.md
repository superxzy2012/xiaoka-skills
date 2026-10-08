---
name: local-asset-versioning
description: Use when versioning or publishing local private assets.
---

# 本地私有资产的版本管理与安全发布

把本机的私有资产（技能库、记忆脚本、知识库笔记）纳入 git 版本管理，或同步到
GitHub 等远端。核心约束是**BOSS 的个人信息绝不进公开仓**，这压倒「备份要完整」。

## When to Use

- BOSS 说「建备份+版本管理」「同步到 GitHub」
- 要把 `/opt/data/skills`、`/opt/data/memories`、知识库笔记等纳入 git
- 要做跨机同步，或发现某类本地资产没有版本历史

## 核心约束（先于流程）

实测扫描技能+记忆目录会命中：手机号（含 12306/抖音账号绑定手机号）、姓名、
英文名、常住区、写字楼名。**凭据类文件（cookie 目录）连脱敏都不做，直接排除。**

## 顺序：脱敏 → 校验 → 提交 → push

四步必须按序，**校验在提交之前**：一旦把未脱敏内容提交进 git，敏感信息就永久留在
git 历史里，事后删文件也清不掉（除非重写历史）。

```bash
scripts/backup_skills.sh "commit message"
```

手工做时按同样顺序，尤其别跳过第 2 步。

### 1. 脱敏

复制工作区文件到暂存目录，按规则替换：

| 类别 | 处理 |
|---|---|
| 手机号 / 姓名 / 英文名 / 区 / 大厦 | 替换为 `【…】` 占位符 |
| `cookies/` 整个目录 | **排除**，不脱敏、不上传 |
| `MEMORY.md` / `USER.md` / `USER_PROFILE.md` | **排除**，个人信息密度最高的三个文件 |
| `__pycache__` / `.cache` / `.venv*` / 嵌入的 `.git` | 排除 |

### 2. 校验（硬门，不过就中止）

```bash
grep -rlE '1[3-9][0-9]{9}|<姓名>|<区>|<大厦>' "$STAGE" | grep -q . && { echo "❌ 中止"; exit 1; }
```

还要二次扫描**已推上去的内容**（contents API 抽查），因为「本地干净」不等于
「远端干净」——上一次误 push 会留下历史。

### 3. 提交

### 4. push（含重试与假成功检测）

## 单一共享目录 → 单一订阅的轮式同步（NAS 当发布节点）

当任务形状是「本机把一个目录持续推到一个中心仓，其他机器各自 pull」时（NAS → GitHub 枢纽 → Mac），
建立一条**轮式**同步链路：写入者只管推，订阅者只管拉。写入者永远不会替订阅者写文件。

### 铁律：先拉后推，且冲突即中止

```
git fetch origin <branch> && git merge --no-edit origin/<branch>
# 有未合并文件 → 立即 exit，绝不 push
```

「推之前先拉」不是为了好看，是为了不覆盖其他订阅者的提交。顺序反了就会静默吃掉别人的提交。
冲突必须中止，不能靠强推绕过；真要重写远端历史，只能用 `--force-with-lease`（见上文）。

### 工作副本放在本地盘，不在共享盘

**git 操作不要在 NAS/网络共享盘的工作目录里跑**——checkout 写远程磁盘比本地 SSD 慢一到两个数量级。
做法：把要发布的目录 `cp -a` 到本地盘（如 `/opt/data/sync/<repo>`）当工作副本，在那里 init/add/commit/push，
推之前重新 `cp -a` 一遍把 NAS 上的最新成果覆盖进去。

### 首次推送前必须报体积

```
git diff --cached --name-only -z | xargs -0 stat -c%s | awk '{s+=$1} END{printf "%.1f MB\n", s/1048576}'
```

把数字写进汇报。推一个 1GB 的仓会变成对方几十分钟的 clone，且 blob 进了历史就删不掉。

### 私有仓 + SSH deploy key

私有中心仓用 `ssh-keygen -t ed25519 -N '' -C '<node>@<host>' -f <path>` 单独一把 key，
`chmod 600`。不要复用已有的登录 key（职责混在一起，且对方仓出错时会连累现有免密登录）。

**交付公钥前必须回验，否则用户贴错了也看不出：**

```bash
grep -E '^ssh-ed25519' <pubkey-file> | ssh-keygen -lf -   # 文件里的行能不能解析
ssh-keygen -lf <private-key>                              # 指纹是否一致
```

指纹一致再交付。用户把公钥贴到仓库 Settings → Deploy keys 时要**勾上 Allow write access**，
并把这一句写进汇报——不勾就是只读，push 会报 403 而不是连接错误。

### 判据：403 与「仓库不存在」不是一回事

token scope 不足时 GitHub 会回 `remote: Write access to repository not granted.` + HTTP 403；
仓库真不存在则是 `Repository not found.`。**这两个错误含义完全不同，猜错会白跑一天。**
对照实验：拿一个肯定不存在的仓名跑同样的命令，看它回什么。推之前先区分清楚是哪个。

### 先搜网段再报「连不上」

要连某台机器做双写却连不上时，扫网段（22/445 等端口）确认它到底在不在，
并对开着的口试多个用户名（`【BOSS英文名】`/`xiaoka`/`hermes`）。区分三种情况并在汇报里分开写：
① 机器不在网段 → 只能靠对方 pull（写成兑底路径，不是失败）；② 在但拒绝公钥 → 需要授权；
③ 在且能进 → 直接推。扫完整段只要 1–2 分钟（`xargs -P 60` 并发），比猜地址快得多。

| 份 | 位置 | 内容 | 用途 |
|---|---|---|---|
| **原件** | NAS 本地 git 仓 | 未脱敏全量 | 零隐私风险的主副本 |
| **脱敏件** | GitHub 公开仓 | 已脱敏 | 异地容灾 + 万一本地全毁能自己捞回 |

原件放 NAS 上一个**普通可写目录**（顶层目录常不可写），语义上属于个人工作区。

## git 踩坑（本机实测，都会造成静默损坏）

**`rsync --delete` 会删掉 `.git/config`，连带删掉 remote。**
`--exclude='.git'` 只排除 `.git` 目录本身，仍会递归删除其内容。必须写成
`--exclude='.git/'`（带斜杠），并在同步完检查 `git remote get-url origin`，
没有就补 `git remote add`。更稳的替代：只删工作区条目（`! -name '.git'`）。

**git 操作一律用显式 `git -C <repo>`，不要依赖调用进程的 cwd。**
一次 `cwd` 未生效就会在当前目录（比如家目录）意外初始化一个仓，把 `.env`、
cookie 全部纳入版本控制。**建仓后立刻核对 `git ls-files | wc -l` 和顶层目录列表。**

**push 报 `! [rejected] main -> main (fetch first)` 不一定是网络问题。**
先 `git fetch origin && git log --oneline origin/main` 确认远端是否真有新提交。
若本地工作目录曾被整体替换，本地与远端会**无共同祖先**，
此时用 `git push --force-with-lease=main:<远端 sha>`（带租约，远端若已被他人
推进则自动拒绝）。裸 `--force` 会覆盖别人的提交，不要用。

**push 报 408/`RPC failed` 时远端可能仍是空的。**
用 API 读实际状态判断，别信本地 refs：
`gh api repos/<owner>/<repo> --jq '"size=\(.size) pushed=\(.pushedAt)"'`
`pushed=null` 或 `size=0KB` = 没推上去。此时不要反复重推，先修因。

**网页域名可能间歇性不可达而 API 域名一直正常。**
push 前用 `curl -s -o /dev/null -w '%{http_code}' -m 10 https://<网页域名>` 探活，
不通就退避 20s 重试（实测 45–75s 恢复）。判据是网页域名而非 API 域名。

**token 不要写进 remote URL。**
`https://user:TOKEN@github.com/...` 会把凭据存进 `.git/config`，且 shell 历史、
进程列表都可能泄露。改用 `git config credential.helper store` +
`~/.git-credentials`（权限 600）。

## 令牌 scope 决定做不到哪一步（多一条：私有仓）

| scope | 能力 | 不含 |
|---|---|---|
| `public_repo` | 读公开库、push 公开库、代码搜索 | **建私有库**（GraphQL 报无 CreateRepository 权限）、**删库**（403 需 delete_repo）、**读写他人私有仓**（403 Write access not granted） |

所以公开仓 + 公开仓备份流程可以全自动，**建私有库、给第三方节点开私有仓写权限、删测试仓
必须请用户在网页操作**。不要为这些操作向用户索要更高权限 token——发一个需要
`repo` scope 的提醒只会让用户以为你卡住了，而正确做法是**把公钥准备好 + 告诉他勾哪个选项**，
让他用他本人的网页登录点两下。

## 收尾清单

- [ ] 脱敏暂存 → grep 校验通过（提交前）
- [ ] 远端 contents API 抽查，确认无泄露
- [ ] `cookies/` 与记忆主文件确认未进仓库
- [ ] remote 已配置且未被 rsync 删掉
- [ ] 需要用户在网页处理的动作已明确告知（建私有库/删仓）

占位符表、目录排除清单、远端二次校验命令、首次建仓顺序见
`references/redaction-and-publish.md`。

多节点轮式同步（NAS 当发布节点推、其他机器各自 pull）的完整脚本骨架见
`templates/sync-subscribe.sh`——含先拉后推、冲突即中止、工作副本放本地盘、
推送前报体积、deploy key 交付回验。改造时只需改顶部 6 个变量。