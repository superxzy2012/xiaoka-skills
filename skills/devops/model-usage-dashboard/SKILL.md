---
name: model-usage-dashboard
description: Use when 要看每天各模型/平台调用量。三源采集+离线看板。
---

# 模型调用看板

## 什么时候用
BOSS 问「最近调了多少」「哪个模型用得多」「免费池还剩多少」「今天花了多少调用」，或需要给模型/平台用量做日/周复盘时。

## 架构（旁路采集，不改动任何网关）

三个数据源归一化到 `/opt/data/usage/usage.db` 的 `calls` 表：

| source | 来源 | 视角 |
|---|---|---|
| `omniroute` | 容器 `omniroute` 的 `/app/data/storage.sqlite` → `usage_history` | 网关真实出口，最全 |
| `wbproxy` | 容器 `wb-proxy` 的 `/app/usage/usage.jsonl` | 8788 平台 |
| `hermes` | 本机 `/opt/data/state.db` → `session_model_usage` | Hermes 会话累计 |

**铁律：网关视角与 Hermes 会话视角不可相加**（同一请求两边都有记录）。看板分开展示。

## 文件

```
/opt/data/usage/
├── collect.py        # 三源增量采集（水位 state.json）
├── or_query.js       # OmniRoute 查询 JS（容器内副本 /app/or_query.js）
├── dashboard.py      # 生成 dashboard.html（自包含，零外网依赖）
├── daily_summary.py  # 每日 Markdown 早报
├── refresh.sh        # collect → dashboard
├── usage.db          # 归一化库
└── dashboard.html    # 看板
/opt/data/scripts/usage_refresh.sh   # cron 入口（必须放这里）
/opt/data/scripts/usage_daily.sh
```

## 发布

NAS 上 `usage-dashboard` 容器（nginx:alpine）挂载 `/volume1/ssd-offload/hermes/data/usage:/usr/share/nginx/html:ro`，端口 `8790`。

- LAN：`http://192.168.199.2:8790/`
- 节点小宝隧道：`http://10.222.222.1:8790/`
- `index.html` 是 `dashboard.html` 的软链

## cron

| job | 频率 | 作用 |
|---|---|---|
| 4a560d9d943d | 每小时 | collect + 重生成 HTML |
| 1ccc7ea4f5e0 | 每日 08:30 北京（expr `30 0 * * *`） | 昨日汇总推飞书 |

## 踩过的坑

1. **`cronjob_manage` 的 `script` 必须是 `/opt/data/scripts/` 下的相对路径**，绝对路径直接报 `Script path must be relative to /opt/data/scripts/`。改法：脚本放 `/opt/data/scripts/`，只写文件名。
2. **`or_query.js` 必须放 `/app/`**，放 `/tmp` 时 `require('better-sqlite3')` 解析不到（node 从脚本所在目录向上找 node_modules）。
3. **`node -e "<JS>"` 经 ssh 会被 shell 引号吃掉**，一律落盘成 .js 再 `docker exec node /app/xxx.js`。
4. **`openai-compatible-chat-<uuid>` 是自定义通道**，uuid 无信息量；按 `account_label` 显示成 `自建·Remote-Aggregator` 之类。
5. **模型名大小写不统一**（`glm-5.3-flash` vs `GLM-5.3-Flash`），聚合前统一 `lower()` 做 key，显示保留首次出现的写法，否则同一个模型被拆成多行。
6. **`request_cost_ledger` 是空表**（0 行），OmniRoute 不记成本；`cost_usd` 全为 0，别做成本卡片误导人。要成本得另接计费源。
7. **Playwright 截图中文变豆腐块**：容器无 CJK 字体。修复：`curl -x http://192.168.199.2:7891` 下 `fonts-wqy-microhei` deb → python 解 ar 归档提取 ttc 到 `~/.fonts` → `fc-cache -f`。只影响截图，不影响 BOSS 浏览器里看页面。
8. **`bar_svg` 的 x 轴标签切片**：原写法 `lab[5:]` 是为 `YYYY-MM-DD` 设计的，小时标签 `"00"` 会被切成空串。改成 `lab[5:] if len(lab) > 5 else lab`。
9. **cron 环境 ssh 可用**（密钥在 `/opt/data/.ssh/`），无需额外配置。

## 改看板

改 `dashboard.py` 后手动跑 `python3 /opt/data/usage/dashboard.py`，nginx 直接读文件，无需重启容器。验证：`curl -s http://192.168.199.2:8790/ | grep -c 'rgba(79,140,255'`（矩阵热力格数）。

## 数据完整性自检

```bash
cd /opt/data/usage && python3 - <<'PY'
import sqlite3
c=sqlite3.connect('usage.db')
print(c.execute("select source,count(*) from calls group by 1").fetchall())
print(c.execute("select min(date),max(date) from calls").fetchone())
PY
```
水位在 `state.json`（`omniroute_id` + wb-proxy 时间戳）。采集日志 `collect.log`，刷新日志 `refresh.log`。
