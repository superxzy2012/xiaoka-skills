# 技能库瘦身（token 预算管理）

常驻提示里每个技能只贡献 name + description，但 400+ 个技能累积起来是数万 token —— 这部分每轮都要付。技能库瘦身 = 把长尾技能从常驻提示摘掉、保留按需可用，换来首 token 延迟和上下文预算。

触发场景：BOSS 说「砍技能 / 技能太多 / 精简技能库」；每轮 token 消耗异常高；技能数 300+ 且大部分是同一类 API 包装。

## 1. 先量化，再决定砍谁

扫所有技能根目录（`skills.create_dir` + `skills.external_dirs`）的 SKILL.md frontmatter，按 **description 字符数** 排序（≈ tokens = chars/3）。**成本在描述，不在正文** —— 正文只在触发时才进上下文。

```bash
python3 <skill>/scripts/audit_skill_library.py --top 25
```

输出按名字前缀聚合（`linkfox-*`、`arkcli-*` 这类前缀往往一家就占 30-45%），这是最快的判定依据：**一族 API 包装全部可摘**，因为它们的知识是「参数怎么填」，需要时读文件即可，不需要常驻触发。

## 2. 保留集怎么定

按 BOSS 的真实业务域定保留集，不按「可能有用」定。典型保留：核心运维/人设、平台接入（飞书/蜂群/A2A）、主机与网络、内容入库流水线、电商全链路、办公文档、行情。

一律可摘：单一第三方 API 的细粒度包装、内容生成器、人物视角/思维框架、一次性研究框架。

**不要摘**：cron 任务或例行流程依赖的技能、`ESSENTIAL_SKILLS` 里的、正在被某个 runbook 明确引用的。

## 3. 落地：`skills.disabled`

Hermes 没有 `hermes skills enable/disable` 子命令（`hermes skills` 只有 trust/browse/install/inspect/list/audit/…），开关就是 config.yaml 里的列表：

```yaml
skills:
  external_dirs:
    - /opt/data/skills
    - /path/to/shared/skills
  disabled:
    - "linkfox-1688-procurement"
    - "115网盘电影字幕匹配 (xiaoka-115-subtitle)"
```

写这个列表的规矩：

- **先备份** `config.yaml` 到 `config.yaml.bak-<用途>-<时间戳>`，出问题一行命令回滚。
- **名字用 JSON 引号包**（`json.dumps(name, ensure_ascii=False)`）—— YAML 里 JSON 字符串合法，能吃掉中文、空格、括号。
- **写完必须 `yaml.safe_load` 回读校验**，确认条数正确、`external_dirs` 没被破坏；失败立刻回滚备份。
- 只替换 `disabled:` 这一段的行，别重排整个文件 —— 注释和缩进是活的。

## 4. 验证：数量 + 名字对得上

改完调 `skills_list`，技能数应该等于「全部唯一名字 − disabled 条数」。

**坑：禁用名字和显示名字可能不一致。** frontmatter 若是 CRLF 或被写坏（例如开头空 `---` 块），加载器会退化成「目录名」，而你从 frontmatter 里解析出来的名字是另一个 —— 这条技能就漏网了。所以扫完要用 `skills_list` 的实际输出对一遍差集，把漏的按**显示名**补进 disabled。

## 5. 关键坑：disabled 技能不能 `skill_view`

```
Skill 'x' is disabled. Enable it with `hermes skills` or inspect the files directly on disk.
```

所以「摘掉但随时能加载」的设计不能靠名字，**索引必须带绝对路径**：

```markdown
- `linkfox-1688-procurement` — 1688采购全流程 — /path/to/skills/linkfox-1688-procurement/SKILL.md
```

用法：`search_files(pattern='关键词', path='<索引文件>')` 定位 → `read_file(<path>)` 读正文照做；要跑它的 `scripts/` 就按路径直接执行。**别整篇 read 索引** —— 300+ 行索引本身也是几千 token。

索引头部写清三条出路：read_file 读正文 / 按路径跑脚本 / 从 disabled 删掉恢复常驻。

## 6. 收尾

- 生效时机：系统提示按会话构建，**新会话**才看到精简后的列表；当前会话不变。
- 回滚：删掉 `skills.disabled` 里那一行即可，不必重启。
- 第二档杠杆：把保留下来的描述压到 40 字内还能再省一截，但会降低自动触发准确率 —— 先只砍长尾，别一步到位。
- 砍完把「已精简 + 索引位置 + read_file 用法」写进记忆，否则下个会话会以为技能丢了。
