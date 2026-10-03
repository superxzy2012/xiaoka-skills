---
name: oss-ecosystem-survey
description: Use when 盘点某平台/领域的 GitHub 开源全景清单。
---

# 开源生态普查：交一份能直接用的清单

与 `find-skills-xiaoka` 的区别：那个技能回答“我该不该自己造”，这个回答“这个领域有什么现成的、
哪些值得看”。BOSS 要的是后者时不要只跑一次搜索就交差。

## 先读 BOSS 的边界词

| BOSS 说 | 含义 |
|---|---|
| 「列个清单」「去看看」 | 只调研，产出 Markdown 清单 |
| 「暂时什么都不要碰」 | **纯只读**：不 clone、不装依赖、不改技能库、不建仓、不 commit |
| 「你看着办」 | 可以动手，但先说方案 |

只读模式下允许的调用：search / repo view / contents / license 查询。
禁止的：clone、tarball 下载、`gh repo create`、`git init`、写技能文件。
**判据不是“风险高低”，是他这句话在不在。**

## 检索：多轮，且要跨类型

单轮查询必然漏。**平台名要按资产类型分别搜**，因为一个生态里同时存在多种东西：

```bash
# 用 gh，token 已配（scope public_repo，5000/小时）
gh api search/repositories -f q="<平台> api python" -f sort=stars -X GET
gh api search/repositories -f q="<平台> mcp"          -X GET
gh api search/repositories -f q="<平台> scraper"      -X GET
gh api search/repositories -f q="<平台> seller automation" -X GET
gh api search/repositories -f q="<平台> agent skills" -X GET   # ← 最容易漏
```

**最后一类（给 AI agent 用的技能包 / SKILL.md 集合）最容易漏但最省事。**
只搜 SDK/MCP 会得出“必须自己封装”的错误结论。

同一平台的两种语言要分开跑（如官方SDK 集中在 PHP/Java，Python 侧另有社区库）。

## 验真：星数会骗人

平台名经常被同名无关项目抢占头部。**每个候选都要读 `name + description + topics` 确认领域归属**：

```bash
gh api repos/<owner>/<repo> --jq '"\(.full_name) | \(.stargazers_count) | \(.description) | \((.topics//[])|join(","))"'
```

用正则过滤而不是肉眼扫（同名干扰有固定形态）：

```python
real = re.search(r'mercado\s?libre|mercadolibre|\bmeli\b', blob, re.I) \
       and not re.search(r'melissa|melis-|mail client', blob, re.I)
```

排除形态：同名词（品牌简称撞邮件客户端/托管平台/工具名）、
同缩写不同行业（ML/AI/QA类通用缩写）、项目内某子模块名与平台同名。

**报告里要把误报单独列一节。** BOSS 需要知道“为什么榜单第一不在清单里”，
否则他会以为你漏搜了。

## 排序：星数是排序起点，不是结论

按星数倒序交差是失败交付。必须补三个维度：

| 维度 | 怎么报 |
|---|---|
| **最后 push 时间** | 超过 2 年没动 → 显式警告「基本等于废弃」 |
| **许可** | MIT/Apache 可用；GPL 传染；无 LICENSE 只能读思路 |
| **适配度** | 头都往往是脆弱爬虫，官方 SDK 可能 5 年没更新；★3 的项目可能正好是 BOSS 的实际场景 |

**在按星数排的表后面，单独加一段「最值得先看的 N 个」，说清为什么。** 这是清单真正的价值。

## 报告骨架

1. **先说最大的坑**（如“星数全是假的，X/Y 是误报”）—— 结论先行
2. 真候选表：仓库 / ★ / 语言 / 许可 / 干什么 / **最后更新**
3. 「最值得先看的 N 个」+ 每个的一句话理由 + 与 BOSS 现状的匹配点
4. **风险提示**：官方 ≠ 活跃、高星 ≠ 高质量、最大星可能是爬虫
5. **下一步选项**，明确标出哪些需要他授权才能动

最后一条铁律：只调研的任务，结尾不要问“要不要我现在就……”来暗示下一步动作，
列选项即可，决定权在他。

## 关联

- 造轮子前的单点查证：`find-skills-xiaoka`
- 抄第三方内容前的引文校验：`ground-truth-discipline`（实测他人开源文档里也有错引）
- 领域背景知识：对应的平台作战手册技能（如 `ozon-mastery`）