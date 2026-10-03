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

## 双份仓策略

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

## Token scope 边界（决定能做到哪一步）

| scope | 能力 | 不含 |
|---|---|---|
| `public_repo` | 读公开库、push 公开库、代码搜索 | **建私有库**（GraphQL 报无 CreateRepository 权限）、**删库**（403 需 delete_repo）|

所以公开仓 + 公开仓备份流程可以全自动，**建私有库和删测试仓必须请用户在网页操作**。
不要为这些操作向用户索要更高权限 token。

## 收尾清单

- [ ] 脱敏暂存 → grep 校验通过（提交前）
- [ ] 远端 contents API 抽查，确认无泄露
- [ ] `cookies/` 与记忆主文件确认未进仓库
- [ ] remote 已配置且未被 rsync 删掉
- [ ] 需要用户在网页处理的动作已明确告知（建私有库/删仓）

占位符表、目录排除清单、远端二次校验命令、首次建仓顺序见
`references/redaction-and-publish.md`。