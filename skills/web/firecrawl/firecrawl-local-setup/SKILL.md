---
name: firecrawl-local-setup
description: 本机 Firecrawl CLI 装法、认证状态与免费替代路径。
version: 1.0.0
author: 小卡
license: ISC
metadata:
  hermes:
    tags: [firecrawl, web-scraping, setup, local-environment]
    related_skills: [firecrawl-build, firecrawl-build-scrape, firecrawl-build-search,
                     agent-reach, crawl4ai, convert-documents-to-markdown]
---

# Firecrawl 本机环境说明

2026-10-04 随 `firecrawl/firecrawl` 的 5 个 build skill 一同装入。
**那些 SKILL.md 全是通用的云端集成文档 —— 这份补充本机实际情况，读本机相关的事先看这里。**

## 装了什么

| 项 | 值 |
|---|---|
| CLI | `/opt/data/.local/bin/firecrawl` v1.25.3（npm 包 `firecrawl-cli`，**ISC**） |
| 技能 | `/opt/data/skills/web/firecrawl/` 下 5 个：`firecrawl-build` + `-scrape` / `-search` / `-interact` / `-onboarding` |
| **PATH** | ⚠️ `/opt/data/.local/bin` **不在默认 PATH 里**，要写绝对路径或先 export |
| 认证 | ❌ **未认证**，`firecrawl --status` 显示 `Not authenticated` |

## 装法踩的坑

**`firecrawl setup build --global` 对 Hermes 无效** —— 它只认 PromptScript / Claude Code 等少数
harness，5 个 skill 全部报 `PromptScript does not support global skill installation`。
**必须手动从仓库 `skills/` 目录拷进 `/opt/data/skills/web/firecrawl/`。**

```bash
# 拉源码（codeload tarball 约 3s；git clone 在 NAS 磁盘上极慢，务必用 tarball）
curl -sL -o fc.tar.gz https://codeload.github.com/firecrawl/firecrawl/tar.gz/refs/heads/main
tar xzf fc.tar.gz
cp -r firecrawl-main/skills/firecrawl-build* /opt/data/skills/web/firecrawl/
```

**`npm install -g` 会失败**（`/usr/local/lib` 不可写），要 `--prefix /opt/data/.local`。

## 认证与额度

5 个 skill 全部声明 `FIRECRAWL_API_KEY` 为**必需输入**（`FIRECRAWL_API_URL` 可选，
只有自托管部署才需要）。

**实测未认证也能跑 `scrape`** —— 因为 `example.com` 是 Firecrawl 官方文档演示端点。
**真实站点不行**，会返回未认证错误。

```bash
# 登录（浏览器 OAuth，需 BOSS 本人在场）
/opt/data/.local/bin/firecrawl login --browser

# 只看状态
/opt/data/.local/bin/firecrawl --status
```

**没有 key 时不要硬试**，换本机已有的免费路径：

| 需求 | 用这个（已装、免费、已验证） |
|---|---|
| 搜索/抓网页正文 | `agent-reach` 技能、`web_search` / `web_extract` 工具 |
| 需要 JS 渲染 | `playwright`（在 `/opt/data/.venv-browser`）+ CDP 桥到 BOSS 的 Chrome |
| 大规模爬取 | `web/crawl4ai` 技能 |
| 页面被 WAF 挡 | `web/blocked-page-recovery` 技能 |
| **本地文件转 Markdown** | `convert-documents-to-markdown`（anydoc，Rust，**免 key**）← 先试这个 |

**注意 Firecrawl 本体是 AGPL-3.0**（CLI 是 ISC）。仓库里自托管也没问题，自用不违规。

## CLI 能干什么（未认证也列出来，方便判断值不值得登录）

`scrape` 单页 / `crawl` 整站 / `map` 站点地图 / `search` 联网搜索 /
`parse` **本地文件转 markdown**（HTML/PDF/DOCX/XLSX/RTF…）/ `interact` 浏览器交互 /
`monitor` 定时抓取对比 / `research` 4300 万篇论文索引（90% 生物医学）/
`developer` GitHub issue/PR/README 索引 / `agent` 让 AI agent 自己抓。

`parse` 与已装的 `convert-documents-to-markdown`(anydoc) **功能重叠**，
且 anydoc 免 key、Rust 更快 —— **本地文件优先用 anydoc，Firecrawl 的价值在联网抓取。**

## 反证条件

什么观察会推翻「不值得登录 key」这个判断：
- BOSS 开始需要**大规模**爬站（几百页以上）且要绕过 WAF —— crawl4ai 和 playwright 会慢到不可用
- 需要 `research`（4300 万论文）或 `developer`（GitHub 全库语义检索）索引 —— 本机没有任何等价物
- 需要浏览器交互式抓取（点按钮、填表单）—— `interact` 是 Firecrawl 独有
