---
name: redacted-public-backup
description: Use when publishing a workspace to a public remote repo.
---

# 脱敏后公开备份

## 什么时候用

| 信号 | 例子 |
|---|---|
| 要把本地目录推到公开/远端仓库 | 「建个 GitHub 仓备份技能库」 |
| 要发布任何含登录态、个人信息的工作区 | 「把笔记同步到云端」 |
| 拿到新 token 后第一件事是上传东西 | — |

**核心原则：公开仓 = 不可撤回。** 泄露后即使删文件，Git 历史、缓存、fork 里还在。
所以顺序永远是 **扫描 → 脱敏 → 复验 → 才推**，不是「先推上去再说」。

## 先问清楚三件事

1. **远端可见性** —— 私有仓也要脱敏（可能有协作者、日志泄露）。只是公开仓风险等级最高。
2. **什么绝对不能上去** —— 登录态 cookie、API key、个人身份信息。先列出来。
3. **token 能做什么** —— `public_repo` scope 建不了私有库（实测报 `does not have the correct permissions to execute CreateRepository`）。
   私有仓需要带 `repo` scope 的 token；没有就老实说「只能建公开仓，必须脱敏」。

## 流程

### 1 · 扫，先拿到清单再动手

```bash
python3 scripts/scan_pii.py <目录>            # 报告命中文件和敏感类型
python3 scripts/scan_pii.py <目录> --json     # 机器可读
```

**按类型分组排除，不要按文件名猜。** 实测文件名判断漏了一整类：
真实登录态在 `memories/cookies/` 下（6 个文件），
但另有 `extract_cookies.py` 和 `references/cookie-export.md` 同名命中——**它们是脚本和文档，不是凭据本体**。
只有内容扫描 + 人工判断才能区分。

排除项分两类，都要排：

- **整个目录排除**：`cookies/`、`*.key`、`*.pem`、`.env`
- **整个文件排除**：`MEMORY.md` / `USER.md` / `USER_PROFILE.md` 这类含身份信息的记忆主文件

### 2 · 脱敏，用替换而不是删除

替换成占位符，保留句子结构，这样 diff 还能看出改了什么：

```
手机号        → 【手机号】
城市/区/大厦  → 【城市区】/【大厦】
姓名/英文名   → 【BOSS姓名】/【BOSS英文名】
```

**误报会有，别把规则当铁律。** 实测 `【BOSS英文名】-Enriquez/MercadoLibre-Clone` 是 GitHub 用户名，
不是本人——全库替换会毁掉数据。规则要窄（用具体全名而非泛化模式），命中后逐条看。

### 3 · 复验：推送前必须阻断

```bash
if grep -rlE '1[3-9][0-9]{9}|<姓名>|<城市>' "$STAGE" | grep -q .; then
  echo "❌ 仍有敏感信息，中止"; exit 1
fi
```

**把这个门写进脚本，而不是靠人记得。** 实测两次出事都是因为跳过了这步。

复验要同时跑**本地暂存区**和**远端已有内容**（远端可能是旧版本带进来的）。

### 4 · 再推

push 前先确认 remote URL 里**没有 token**：

```bash
git -C "$REPO" remote get-url origin | grep -q 'ghp_' && echo "⚠️ URL 含 token，先清掉"
```

token 写进 remote URL 后会留在 `.git/config`，即使后来 push 成功也要清。
用 `credential.helper=store` + 独立的 `~/.git-credentials`（权限 600）承载凭据。

## 凭据不进任何脚本字面量

remote URL 只是泄露途径之一。**更隐蔽的是自己写的核查/探测脚本**——
把 token 写成 `GH_TOKEN` 字面量，然后跟着笔记和工作区一起归档进 NAS、推上远端。

**规则：脚本一律从环境变量读凭据，文件里不出现 token 形态的字符串。**
归档任何 `.py`/`.sh` 前扫一遍 `gh[pousr]_[A-Za-z0-9]{20,}`。

**工具层可能自动打码**（读文件时显示 `«redacted:ghp_…»`）——**那是显示层，不是磁盘**。
看见打码不等于没泄露。

**凭据文件权限一律 600。** `gh` 的 `hosts.yml` 配完可能是 644，要显式 `chmod 600`。

### 扫描命中先分真假再处理

公开仓里出现 token 形态的命中，两种可能：

- **占位符**：官方文档写法 `ghp_xx...xxxx`，含 `xx` / `xxx` / `YOUR`
- **真值**：40 位混合大小写随机串

**按内容判断，不靠长度直觉。** 先看它出现在配置示例还是真实赋值处，
再用前缀特征比对；确认是占位符才放过，是真值立即清理并撤销该 token。

反过来，**扫到东西时也要看全范围**：暂存区干净不代表归档目录干净——
归档脚本、核查脚本常常另存一份副本在别处。

## 四个会把备份搞坏的 git 坑

### 坑 1 · `git init` 落错目录 → 把家目录全纳进仓

用 `subprocess` 的 `cwd` 参数跑 git 时，如果实际调用被包在 `bash -c` 里，`cwd` 不会传给 git，
于是仓建在了当前工作目录（可能是 `$HOME`）。实测一次 `git ls-files` 返回 **26,598 个文件**，
包含 `.env` 和登录态。

**规则：每条 git 命令都用 `git -C <绝对路径>` 显式指定仓库，不要依赖 cwd。**
建完仓立刻 `git ls-files | wc -l` 核对数量级——异常大就是落错了。

### 坑 2 · `rsync --delete` 会删掉 `.git/config`

`--exclude='.git'` **不够**，必须 `--exclude='.git/'`（带尾斜杠只匹配目录本身）。
排除写法不对时 remote 配置被删干净，push 直接失败，且没有报错提示。

**规则：同步工作区到已有仓时用 `--exclude='.git/'`；更稳的是不用 rsync，改成
`find "$REPO" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +`。**

### 坑 3 · 手工放在仓里的文件会被下次同步删掉

`README.md`、`.gitignore` 这类只存在于仓库、不来自源目录的文件，一次同步就没了。

**规则：仓库门面文件由备份脚本生成，或存在源目录里让脚本一起搬。**

### 坑 4 · 历史分叉后 `push` 报 `fetch first`

真实原因不是「远端有新提交」，而是**本地 `.git` 与远端已经无共同祖先**
（首次 push 其实失败了，本地却记成已推送）。诊断：

```bash
git -C "$REPO" merge-base main origin/main   # 空输出 = 无共同祖先
gh api repos/<owner>/<repo> --jq '.size'     # 0KB / pushed=null = 远端其实是空的
```

**规则：区分「网络断了」和「历史分叉」看 `merge-base` 和远端 size，不要靠 push 报错信息猜。**
确认远端只有自己建的提交后，用带租约的覆盖推送（远端有别人的新提交会自动拒绝）：

```bash
SHA=$(git -C "$REPO" rev-parse origin/main)
git -C "$REPO" push --force-with-lease=main:"$SHA" origin main
```

force-push 属破坏性操作，**必须让用户明确说「继续」再执行**，不要自己按。

## 双份备份（本机实测组合）

| 位置 | 内容 | 作用 |
|---|---|---|
| NAS 本地私有仓 | 原样，不脱敏 | 零隐私风险的本机版本管理 |
| 公开远端仓 | 脱敏后 | 异地备份 + 本机坏了能自己捞回来 |

两份互补，成本只有几分钟。公开仓那份是「我坏了还能用」，私有那份是「完整原件不外泄」。

## 汇报纪律

- 说「已备份」前先核对**两端 sha 一致**，不是只看本地 commit 成功
- 说「没有泄露」前要给出**远端实际内容的抽检结果**，不是只看暂存区
- 推不上去时如实说「本地已保存，下次自动重试」，不要把本地成功说成全部完成

## 关联

- `third-party-repo-vetting` —— 吸收外部开源前的评估流程
- `ground-truth-discipline` —— 报告数字前先验内容