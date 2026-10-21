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

### 2.4 从短视频/画面定位开源项目（2026-10-03 实战）

抖音只给中文口播、不给仓库名时的完整流程：

1. **`ingest.py` 入库**（转写常漏掉画面上的仓库名）
2. **`ffmpeg` 抽帧 → 降 480px 宽 → `rapidocr_onnxruntime` OCR**（720px×12 张会超 420 秒）
3. **拿 OCR 读到的英文描述原文做 GitHub 全文检索** —— 这是命中率最高的一步。
   实例：OCR 读到 `Convert Word, PowerPoint, Excel, OpenDocument, RTF, EPUB, CSV, and PDF to clean Markdown`，
   直接当 `search/repositories?q=` 的 query 一次命中 `firecrawl/anydoc`。
   比猜仓库名（猜了 4 个全 404）、比用中文关键词都强。
4. **回源硬核实所有数字**，标注不吻合项

**OCR 的数字不可信，坑实例**：视频画面显示「★22.3k / 60 Fork」，实测 forks=1,417、watchers=60 ——
OCR 把 `1.4k` 和 `60` 读串了。**star/forks/watchers 三个字段必须分别取，不能凭画面位置对应。**

**排除干扰项**：同组织同语言的兄弟仓库最像。`firecrawl/pdf-inspector`（★19,472，同为 Rust、同组织）看着完全对，
但只做 PDF 不支持 Office —— 最终正确答案 `firecrawl/anydoc` ★22,472。
**判定依据要比对 README 描述原文，不要只看 star 量级和命名模式。**

**search API 的坑**：`gh api -X GET search/repositories -f q="..."` 里的中文/长 query 必须能被 GitHub 接受，
返回空时先换英文原文再试；`-f` 不加 `-X GET` 会变 POST（`orgs/X/repos` 会报 403 admin access）。

### 2.4.1 短视频吹的和仓库实际的不一致（必查三项）

口播稿是营销文案，**默认不信数字与范围，一律回源**：

1. **「支持 N 种工具」要数表格**。实例：口播说「十种主流 AI 工具」，README 的 supported-agents 表格只有 6 个。
   数 README 里的 `<td>` / 列表项，不要采信口播。
2. **视频常演示的是上一代架构**。先搜 README 里的 `New:` / `Breaking` / `legacy` / `v0.x` 字样，
   再看有没有 `legacy` 分支或旧 tag。实例：视频讲「Mac 跑 UxPlay + Python server」，
   而 README 开头写着「the computer is gone」——现在板子自己当接收器，旧实现留在 `legacy` 分支。
   笔记里必须标明「视频讲的是旧架构，当前版本已改为 X」，否则读者照着装会懵。
3. **star/fork 只认 API**，画面 OCR 与口播都会过时或读串（见上一节的 22.3k 实例）。

### 2.4.2 许可证判定的两个假警报（`scripts/resolve_license.py` 已修）

- **`All rights reserved` / `Copyright (C) 20XX X` 不是「专有」**。这类版权声明与 MIT/Apache 完全兼容，
  大厂开源项目（如腾讯系）几乎都在 MIT 正文前加一句。判专有只认 `proprietary` / `confidential`。
- **`NOASSERTION` 不是「冲突」，是「API 认不出」**。GitHub licensee 遇到自定义措辞就返回 NOASSERTION，
  必须回源读 LICENSE 正文自行判定，输出 `note` 而非 `conflict`。
- 改这两条规则后必须跑 `--selftest`（当前 12/12），规则顺序敏感：禁商用/专有必须排在 MIT/CC0 之前。

### 2.5 官方文档优先于猜 URL（2026-10-03 实战）

**实例**：配mihomo 规则集时，我按记忆猜 `Loyalsoldier/geoip/release/text/cn-domain.mrs` —— 全404。查 mihomo 官方文档 `wiki.metacubex.one` 才找到真实地址（MetaCubeX 自己的 `meta-rules-dat/meta/geo/geosite/cn.mrs`）。

**规矩**：任何「填一个 URL」的字段，先用官方文档或 repo contents API 确认路径存在，再写进配置。404 的正确反应是停下来查，不是换个域名再猜。

**GitHub 搜索的两个坑**：
- `MetaCubeX/mihomo` 在 GitHub 上是**同名撞车的非项目仓库**（星穹铁道数据，Python，★34,606）。真正的 mihomo 内核不在这个名字下。**搜到仓库名不等于找到项目，必须看 language + description 是否与预期一致。**
- 中文 query 必须 URL 编码（`urllib.parse.quote`），否则 gh search 返回空而不报错。

**现成方案可能不适用**：搜「clash 旁路由」出来的全是 OpenWrt 生态（passwall ★9,943 / homeproxy ★1,087），它们依赖 LuCI + OpenWrt 内核，在 UGOS/Debian 裸机上跑不了。**判断现成方案先看它依赖什么运行时，不能只看 star 数。**

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

## 把第三方技能包装进 Hermes（并铺到蜂群）

仓库自带 installer 时**用它**，别自己搬文件 —— 它会同时处理分类目录、辅助脚本和卸载路径。

```bash
# 1) 取源码。本机 git clone 会超时，npx -y github:owner/repo 会被 npm 的 git 依赖拦截
gh api repos/<owner>/<repo>/tarball/main > /tmp/r.tgz
mkdir -p /tmp/r && tar xzf /tmp/r.tgz -C /tmp/r --strip-components=1

# 2) 先 dry-run 看它要写哪儿，再真装（落点 /opt/data/skills/<category>/<skill>/）
cd /tmp/r && node installer/install.js --only hermes --dry-run
node installer/install.js --only hermes
```

- **`--only <agent>` 是必须的**：installer 默认遍历 30+ 个 agent 的配置目录，没装的也去建，容易留下垃圾。
- 装完用 `skills_list` 确认注册。**技能是每次会话扫盘加载：本机立即生效，云端 gateway 要重启。**
- **验证是真跑一次，不是看文件在不在**：同一道题普通模式 / 技能模式各跑一遍，比字数和事实完整度。
  实测某压缩型技能 256 字 → 150 字（−41%）且事实不丢，才算生效；只 `ls` 到目录就报「已装」是假验收。

**铺到蜂群**：技能在各节点是**实体拷贝，不是软链**，共享库改了不会自动到别人家 —— 每个节点都要显式 cp：

| 节点 | 落点 | 备注 |
|---|---|---|
| 本机（小卡） | `/opt/data/skills/<cat>/` | installer 默认落这里 |
| 共享库 | `/opt/nas/volume2/2-AI/skills/` | 扁平结构，无分类子目录 |
| 云端星期五 | `~/.hermes/skills/productivity/` | 改完 `systemctl --user restart hermes-gateway` |
| NAS 贾维斯容器 | `docker exec hermes-ancgm` 内 `/opt/data/skills/` | 宿主路径 `/volume2/hermes/ancgm-home/skills`；容器能看到 `/opt/nas/volume2` |

`scripts/distribute_skill.sh <skill...>` 一条命令做完上面四步。铺完在管理群发一条通知（Feishu API + `/opt/data/.env` 凭据），**用返回的 `message_id` 回读确认**，`code=0` 只代表接口收下了。

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
