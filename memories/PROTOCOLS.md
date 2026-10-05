---
layer: 3
name: 小卡 · 长期工作协议
updated: 2026-10-04
---

# 小卡 · L3 协议层（长期有效的约定）

## 1. Obsidian 知识库
| 项 | 值 |
|---|---|
| Vault 根 | `/opt/nas/volume2/2-AI/obsidian_vault` |
| 笔记总数 | 2972 篇（建库时） |
| 写入权限 | ✅ 已验证可写 |
| 版本控制 | vault 内有 `.git` |
| 主控台 | `/opt/data/obsidian_vault`（SOUL 提到的软链/主目录，尚未创建） |

## 2. 小卡专属目录（已建）
- `15-小卡工作区/` — 小卡的任务产出总目录
  - `A股实盘/` — 每日行情播报笔记
  - `抖音采集/` — 抖音视频抓取入库
  - `生活服务/` — 天气/订票/快餐
  - `记忆快照/` — 4 层记忆的库内镜像

## 3. 抓取管线（已验证）
| 数据源 | 状态 | 说明 |
|---|---|---|
| 腾讯行情 `qt.gtimg.cn` | ✅ 可用 | A股实时行情，中文名 GBK |
| 新浪 `hq.sinajs.cn` | ✅ 可用 | 需 Referer 头 |
| 东方财富 push2 | ❌ 超时 | 偶发 exit=56，别用 |
| 腾讯分时 `web.ifzq.gtimg.cn` | ✅ 可用 | 分时数据，可画图 |

## 4. 已交付的定时任务
见 `/opt/data/memories/PROTOCOLS.md` 同目录的 cron 注册表 → 实际以 `cron_manage` 内的任务为准。

## 5. 抖音抓取约束
- 抖音有反爬 + 登录墙：优先尝试公开接口/分享链接
- 遇到登录墙：停下来问 BOSS，不用猜密码
- 产物格式见 `15-小卡工作区/抖音采集/模板.md`

## 6. Windows 本机执行（pc.sh）— 2026-10-04 打通
| 项 | 值 |
|---|---|
| 入口 | `/opt/data/bin/pc.sh "<命令>"` |
| 身份 | `xiaoka` — 受限用户，非管理员，无 sudo |
| 远端 shell | **PowerShell**（分隔用 `;`，不要用 `&&` / `&` / `\|\|`） |
| 可读 | 自己的家目录、`C:\ProgramData`、公共目录 |
| 不可读 | `C:\Users\EDY\` 下的一切（拒绝访问，**这是设计如此，不要试图绕过**） |
| 网络 | 本机 IP 随网卡切换（以太网静态 `.184` / WLAN 动态 `.70`），pc.sh 自动探测，无需改脚本 |
| 边界 | 需要管理员权限的操作（装软件、改系统配置、动 EDY 的文件）→ 停下来问 BOSS，别硬试 |

示例：
```bash
pc.sh "whoami"                                  # -> super\xiaoka
pc.sh "Get-ChildItem C:\ -Name | Select-Object -First 10"
```

## 7. 浏览器 CDP 桥
`browser.cdp_url` → BOSS 的 Windows Chrome（带登录态，四站已核实）。
**IP 会变**：改动时需同步 `config.yaml` + `memories/{zsxq_ingest,zsxq_ingest2,zsxq_ingest3,selfcheck,extract_cookies}.py`。
