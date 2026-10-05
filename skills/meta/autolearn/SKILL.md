---
name: autolearn
description: Daily self-directed GitHub scouting for new projects.
version: 1.0.0
author: 小卡
license: MIT
metadata:
  hermes:
    tags: [autolearn, github, discovery, cron, self-improvement]
    related_skills: [find-skills-xiaoka, third-party-repo-vetting, ground-truth-discipline]
---

# 主动学习（Autolearn）

BOSS 2026-10-04 要求：**「主动学习——每天自己找新东西学，不用我发链接」**。

本技能 + `memories/autolearn.py` + cron job **`e2788da16dfd`**（每日 09:37）组成每日自动巡检。

## When to Use

- **定时任务在跑**（cron `e2788da16dfd`，每日 09:37）—— 多数情况你不用手动调
- BOSS 说「去找找有什么新工具 / 最近有什么好项目 / 主动学点东西」
- 想改关注方向（改 `autolearn.py` 的 `TOPICS`）
- 扫描结果不想要了 / 想让它重新推荐某个项目（删 `autolearn_state.json` 里对应条目）
- **不要用**：BOSS 直接给了链接 —— 走 `ingest.py` 抖音入库或 `find-skills-xiaoka`，更快更准

## 为什么需要它

已有能力都是**被动触发**的：

| 已有 | 触发方式 | 缺口 |
|---|---|---|
| `find-skills-xiaoka` | BOSS 发链接才跑 | 不主动 |
| `agent-reach` | 我发搜索才跑 | 不主动 |
| 抖音入库 `ingest.py` | BOSS 发链接才跑 | 不主动 |

`autolearn` 是**唯一主动的**那个：每天自己上 GitHub 找新项目并交日报。

## 用法

```bash
python3 /opt/data/memories/autolearn.py              # 扫描 + 写日报 + 更新黑名单
python3 /opt/data/memories/autolearn.py --dry-run    # 只看会做什么，不写任何文件
python3 /opt/data/memories/autolearn.py --selftest   # 自检（8 项）
```

必须用 `/opt/data/.venv-browser/bin/python`。

## 工作原理

1. 读 `memories/autolearn_state.json` 里的 `seen` 黑名单，跳过已推荐的
2. 按 5 个兴趣方向搜 GitHub —— **只捞近 12 个月新建的仓库**（`created:>YYYY-MM-DD`）
3. 过滤：`star` 低于阈值 / block 词（awesome-、roadmap、interview…）/ 主题内重复
4. 打分：log 曲线体量 + 新鲜度加权（近30天 +25，>1年 -10，<100星 -30）
5. 写日报到 `<vault>/15-小卡工作区/生活服务/主动学习/YYYY-MM-DD-主动学习日报.md`
6. 把推荐的记进 `seen`（**只有真推荐过的才记**，low/block 不污染黑名单）

## 它绝不自动装

扫描 → 交日报 → **停下等 BOSS 说装哪个**。装之前必须：
- 回源硬核实 star / license / 最后 push
- **真跑一次验证**（不是只读 README）
- GPL/AGPL 先提醒 copyleft

理由：装错了要回滚，而 BOSS 只给一句话的时间成本。

## 兴趣方向（TOPICS）

按 BOSS 历史行为归纳 —— 他反复让我找 GitHub 开源项目：

1. Agent/记忆
2. Skill 生态（SKILL.md / Claude skill）
3. 文档处理
4. 爬取/数据获取
5. 效率工具

**方向要定期换** —— 同一批查询式跑久了会漏掉新领域。改 `autolearn.py` 的 `TOPICS` 列表即可。

## 踩过的坑

### ⚠️ 最致命：cron 会静默死亡（2026-10-04 真实 bug，已修）

**症状**：第一天扫到 10 个，第二天 0 个，第三天起永久 0。

**两个原因叠加**：
1. `TOPICS` 每个方向只有**一个**固定查询式 → GitHub 返回结果高度重叠
2. `seen` 黑名单**无 TTL** → 扫过一轮后所有结果被永久跳过

**修复**：
- 每个方向配**多个查询式**，按 `date.today().toordinal() % len(queries)` **按天轮换**
- `seen` 的 `recommended` 条目加 **90 天 TTL**（`prune_seen()`），过期重新可推荐
- `skip:low` / `skip:block` **永久保留** —— 低星和 block 是永久判断，重查没意义

**验证方式**：黑名单不变的情况下换查询式，从 0 个变成 12 个。
**改任何过滤逻辑后必须这样验一次** —— 只看「代码里有没有轮换」是自欺欺人。

### 其他坑

- **`gh api -X GET search/... -f q=...` 必须显式 `-X GET`**，否则 `-f` 变 POST，`orgs/X/repos` 会报 403 admin access
- **不加 `created:>` 门槛会天天重复捞老项目** —— crawlee 常年霸榜，看着像「新发现」其实早就推过
- **block 词要拦 `awesome-`** —— 那类仓库几百上千且内容是链接堆，无学习价值
- **日报文件名要带次序号** —— 同一天可能跑两次（手动 + cron），固定名会覆盖上一份有内容的
- 状态文件必须**原子写**（写 .tmp 再 `os.replace`），cron 中途被杀不能留半截 JSON

## 自检项（12）

新鲜项目分 > 僵尸项目分 / 小项目被压分 / block 拦 awesome- 且不误伤 /
状态往返一致 / 检索带时间门槛 / 门槛实测有效（对比不带的时间戳）/
95天前 recommended 被清理 / 今天的保留 / skip:low 永久保留 /
查询式按天轮换 / API 可达。

**改任何逻辑后必须重跑 `--selftest`** —— 没自检的脚本可能一直假 PASS。
