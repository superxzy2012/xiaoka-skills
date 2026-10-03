---
name: find-skills-xiaoka
description: Use when 需要做某类任务且怀疑「已经有现成方案」时——写脚本、装工具、找数据集、蒸馏书籍、建工作流。强制先查本机技能库+GitHub 开源，再决定是否自己造。含本机实测的开源检索命令与踩坑清单。
---

# 先找轮子，再造轮子

## 触发条件（满足任一就必须先查）

| 信号 | 例子 |
|---|---|
| 你正要写一个脚本解决「通用问题」 | 「写个脚本把 md 转成 PDF」 |
| 你正要蒸馏/整理一批资料 | 「把这 5 卷书做成技能」 |
| 你发现自己在实现一个「已知算法/标准格式」 | 「自己实现 PDF 解析」 |
| 任务耗时 >30 分钟且有通用解 | 「搭一套部署流程」 |
| **BOSS 说「站在巨人肩膀上」** | 直接触发 |

**不触发**：只针对 BOSS 这台机器/这个项目的一次性小改动。

## 三级查找顺序

### 1. 本机技能库（最快，先查这里）

```bash
ls -d /opt/nas/volume2/2-AI/skills/*关键词*
```

已知的 finder 类技能（找到后 load 它，而不是自己写）：
- `find-skills` / `skill-finder` / `find-skills__skillhub` —— 场景驱动 + 关键词搜索技能库
- `e-commerce-find-skills` —— 电商专用
- `skill-creator` —— 确认没有现成技能后才造
- `skill-scanner-guard` —— 装第三方技能前的安全扫描

### 2. GitHub 开源（本机实测可用，见踩坑）

```bash
# 仓库搜索（无需认证，中文必须 URL 编码）
curl -s -m 20 "https://api.github.com/search/repositories?q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" '毛选 markdown')&sort=stars&per_page=5"

# 看仓库结构与文件大小
curl -s -m 20 "https://api.github.com/repos/<owner>/<repo>"
curl -s -m 20 "https://api.github.com/repos/<owner>/<repo>/contents/<path>"

# 直接读单个文件（contents 接口 + base64，比 clone 可靠）
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/<path>" | python3 -c "import sys,json,base64;print(base64.b64decode(json.load(sys.stdin)['content']).decode())"

# 下载整个仓库（codeload 比 git clone 可靠）
curl -sL -o r.tar.gz https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main
```

### 3. 官方文档 / PyPI / npm

搜 `site:docs.<project>.org` 或直接装包。**标准库的能用就别装第三方。**

## GitHub 已配好（2026-10-02 实测可用）

```bash
gh --version          # 2.102.0，已装在 /opt/data/bin/gh，软链到 /opt/data/.local/bin/gh
gh search repos "毛选" --limit 5
gh repo view <owner/repo>
```

**未配 token**：仓库搜索/查看能用，代码搜索和 push/fork 需要认证（见下方「BOSS 能做的事」）。


### 🔑 Token 已配（2026-10-02）

`gh auth status` ✅ 通过，scope `public_repo`（读写公开库）。
凭据在 `/opt/data/home/.git-credentials`（600）+ `~/.config/gh/hosts.yml`，**均在账号目录，不在共享区**。

| 能力 | 状态 | 限额 |
|---|---|---|
| 仓库搜索 | ✅ | 5000/小时 |
| **代码内容搜索** | ✅ **（新增）** | 5000/小时 |
| 读文件 / clone / tarball | ✅ | 无限制 |
| 可见 BOSS 的私有库 | ✅（1 个） | — |
| push / PR / Issue | ✅ | — |

**代码搜索的正确用法**（GitHub 仓库搜索对长 query 很弱，代码搜索强很多）：

```bash
# ✅ 用短词，不要长自然语言
gh search code "ground-truth-discipline SKILL.md" --limit 8
gh api search/code -f q='verify_quote selftest filename:verify_quote.py' -X GET

# ❌ 无效：仓库搜索不吃长句
gh search repos "quote verification source citation skill agent"   # 返回空
```


### 拉取脚本 `scripts/gh_pull.sh`

```bash
gh_pull.sh <owner/repo>              # 整仓（--depth 1 --filter=blob:none）
gh_pull.sh -f <owner/repo> <路径>     # 单文件（contents API，不落盘负担）
gh_pull.sh -t <owner/repo> [ref]     # tarball（绕过 git 协议）
```

### ⚠️ 本机 clone 慢的根因（重要）

**不是网络问题，是 checkout 写 NAS 磁盘慢。** 实测同一个 2.3MB 仓库：

| 方式 | 耗时 |
|---|---|
| `git clone --depth 1` | **180s 超时** ❌ |
| `git clone --depth 1 --no-checkout` | 1.9s ✅ |
| codeload tarball | 3.1s ✅ |

curl 走 HTTP/2 拉 200MB 只要 16s，所以**网络完全正常**。
git 默认会 HTTP/2（报 `Error in the HTTP2 framing`），已全局设 `http.version=HTTP/1.1`。

**结论：优先 codeload tarball 或 contents API，别用裸 clone。**


## 造轮子前查 GitHub：实测案例（2026-10-02）

我今天造的三个轮子，用带 token 的代码搜索复查：

| 我造的 | GitHub 搜到的 | 结论 |
|---|---|---|
| `verify_quote.py` 引文回源校验 | 只有 `FairladyZ625/codex-internal-agent-orchestration` 提到同名纪律，但只是「内容边界清单」里的一行 | **没有现成实现**，保留自建 |
| `kb_audit.py` 知识库体检 | `open-compress/claw-compactor`、`glitch-rabin/swarma` 等 8 个 SKILL.md 沾边 | 都是通用 skill，**无现成体检实现** |
| `gh_pull.sh` 拉取脚本 | 无命中 | 保留自建（但已吸收 OSS 毛选技能的 tarball 路径） |

**教训**：代码搜索用**短词 + 文件名过滤**，长自然语言在 GitHub 搜索里几乎必然返回空。
先搜一次（约 3s）比自建一个 200 行脚本便宜得多。

## 本机踩坑清单（全部实测）

| 坑 | 现象 | 解法 |
|---|---|---|
| `gh` 未安装 | 已装 **2.102.0** 到 `/opt/data/bin/gh` | 软链到 `/opt/data/.local/bin/gh`（PATH 里唯一可写目录）|
| 无 GitHub token | 代码搜索 API 不可用 | 仓库搜索/contents 可用；代码搜索改用 web_search 或让 BOSS 配 token |
| **git clone 超时** | 180s 拿不到 | 根因是 checkout 写 NAS 慢，用 `--no-checkout` / codeload tarball（见上）|
| 搜索接口中文未编码 | `400 Bad request` | 必须 `urllib.parse.quote` |
| 本会话无 vision | 看不到图片/SVG 效果 | 改用文字描述或让用户看 |
| web_extract 是 keyless 模式 | `CRAWL_NOT_FOUND` | URL 不在索引就换工具，别调参数 |

## 找到之后：不要直接抄

**开源 ≠ 正确。** 抄之前必须过校验：

1. **许可检查**：MIT/Apache 可直接用；GPL 传染；无 LICENSE 的别抄代码（可读思路）
2. **引文/数据回源**：别人的方案也可能是凭记忆写的。
   实例：`tocekuma/maoxuan-skill` 的 problem-routing.md 里 30 条引文有 4 条是真错引。
   用 `ground-truth-discipline/scripts/verify_quote.py` 验一遍。
3. **保留出处**：拷贝的外部文件放到 `references/oss-<repo>/`，
   连同 LICENSE 和 `UPSTREAM-*.md` 一起留，别混进自己的产物。

## 决策规则

```
现成方案能用（过许可 + 过校验）
  → 直接用，标注出处
现成方案能用但有缺陷
  → 用它的结构/思路 + 自己补强，把差异写进 references/开源方案对比.md
现成方案都不行
  → 才自己造，且必须说明「为什么不用现成的」
```

**已做的对比存档**：
- `maoxuan-jinghua/references/开源方案对比.md` —— 找到 7 个开源毛选方案，逐条验引文
- `maoxuan-jinghua/references/oss-maoxuan-skill/` —— 上游原文（MIT）+ LICENSE

## 自检：这次是不是在造轮子？

写新技能前问自己三句：
1. 本机技能库里有没有？→ `ls /opt/nas/volume2/2-AI/skills/*关键词*`
2. GitHub 有没有？→ 搜一次，30 秒
3. 找到的能不能直接用？

三问都过了才动手写。**跳过前两问就是浪费。**
