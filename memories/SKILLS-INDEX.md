# 小卡技能索引卡 SKILLS-INDEX

> 建卡：2026-10-18 T-015 | 家底：本地 36 + 共享库 351
> 用法：**接任务先查这张卡，定位首选技能，再 skill_view 加载**，不要每次翻 351 个库。
> 原则（BOSS 定调）：更快、更智能，不追求全能——所以每个场景只列**首选 3-5 个**，其余按关键词归档不展开。

---

## 🛒 场景一：跨境电商（最强项）

| 首选技能 | 什么时候用它（一句话） |
|---|---|
| `ozon-to-product` / `ozon-product-to-listing` | Ozon 选品→上架一条龙；给链接/品类要选品、要做 listing 时 |
| `ozon-listing-publish` / `ozon-seller-card-edit` | 真正在 Ozon 卖家后台**执行**上架、改卡、冲内容评级（Playwright over CDP） |
| `ozon-price-index-green` / `ozon-price-archive-ops` | 价格指数整改（无指数/红标）、批量改价归档 |
| `ozon-zero-order-diagnosis` / `ozon-cert-selfcheck` | 零订单诊断、质量证书/10-01 强制认证自查 |
| `linkfox-amazon-search` / `linkfox-keepa-*` / `linkfox-junglescout-*` | 亚马逊选品/竞品/历史价格（LinkFox 真实数据） |
| `linkfox-ruiguan-*` / `linkfox-maidalv-*` | 上链接前查 TRO、商标/专利/版权/外观侵权 |
| `linkfox-1688-*` / `1688-supplier-outreach` | 1688 找货源、查阶梯价、旺旺发询盘、下单 |
| `linkfox-echotik-*` / `linkfox-temu-*` / `linkfox-damai-mercado-*` | TikTok Shop 数据、Temu 选品、美客多市场洞察 |

**关键词兜底**：要某平台某动作先在共享库 `ls /opt/nas/volume2/2-AI/skills | grep -iE 'ozon|amazon|1688|tiktok|temu|mercado|shopify'`。
**方法论闸门**：`product-selection`（选品框架）、`ozon-compliance-gate`（合规闸门）、`quality-audit`（listing 质检）、`crossborder-ecommerce`（SOP+KPI）。

## 🎬 场景二：视频/内容抓取入库

| 首选技能 | 什么时候用它 |
|---|---|
| `video-ingest-pipeline` / `douyin-obsidian` | 收到抖音/B站链接，下载→转写→提炼→入 Obsidian（**默认入口**） |
| `ingest.py`（memories 脚本） | 一键入库命令：`python3 /opt/data/memories/ingest.py <链接> [--keyword 标签]` |
| `douyin-kb-feed` / `douyin-batch-import` | 批量抓某个抖音号全集、批量导入投喂分公司 GM |
| `realtime-video-understanding` | 实时/流式理解视频、RTSP 摄像头、连续图集（ffmpeg 抽帧+视觉模型） |
| `openai-whisper` / `openai-whisper-api` | 纯音频/视频转写字幕（本地 CLI 免费 / API 快） |
| `local-image-ocr` | 只需要把图片/截图里的字读出来 |

**关键坑（已在技能里）**：抖音原生提取器被 Argus 风控 403 封死，走 yt-dlp + douyin-cdp 插件（CDP 拿直链），cookie 再新都没用；CDP 建标签必须 `background=True` 不抢 BOSS 前台。视频提到开源工具默认直接装（先 OCR 抽帧拿仓库名→回源核实→真跑验证）。

## 🔧 场景三：运维 / agent 管理

| 首选技能 | 什么时候用它 |
|---|---|
| `hermes-agent`（autonomous-ai-agents 下） | 配置/扩展/排查 Hermes 本体、cron、插件、config |
| `model-routing` | 切大脑模型、确认实际路由、通道 401/503（先跑 `memories/channel_check.py`） |
| `openclaw-ops` / `openclaw-mcp-tool-troubleshoot` | OpenClaw 网关运维、agent 拿不到 MCP 工具/读不到本机文件 |
| `nas-docker-deploy` / `nas-manager` | 在 NAS 上部署/巡检 docker 容器、媒体库、字幕 |
| `mac-cdp-chrome-9222` / `remote-browser-cdp-bridge` | 接管 BOSS 已登录 Chrome（9222）、远程 CDP 浏览器 |
| `feishu-13bots-tester` / `agent-down-doctor` | 13 个飞书 bot 健康巡检、bot 在群里不响应/零产出诊断 |
| `windows-remote-access` / `macos-*` 系列 | 从 macOS 管 Windows、Mac 磁盘/内存清理、目录迁移 |

**日常运维脚本（memories/）**：`selfcheck.py`（每日自检，已含通道检查）、`channel_check.py`（通道 ping）、`astock_reporter.py`、`autolearn.py`、`kb_audit.py`、`refresh_douyin_cookies.py`、`cdp.py`。

## ✍️ 场景四：内容生产 / 知识沉淀

| 首选技能 | 什么时候用它 |
|---|---|
| `yuanliuwei-writer` / `wechat-formatter` / `wechat-cover-generator` | 写 BOSS 风格公众号短文、排版、封面图 |
| `content-planner` / `ai-trending-topics` | 公众号选题决策、内容日历、AI 爆款选题挖掘 |
| `obsidian` / `book-note-taking` / `pdf-processor-cn` | 笔记入库、PDF/书转结构化笔记、PDF 处理 |
| `nano-banana-pro` / `linkfox-aigc-imagegen` / `baoyu-infographic` | AI 生图/修图、电商图、信息图 |
| `data-analysis-zh` / `chartgen` / `qclaw-data-analyst-pro` | 数据分析、出图、给结论（销售/财务/运营） |
| `powerpoint` / `docx` / `xlsx`（productivity 下） | 生成/编辑 PPT、Word、Excel |
| `maoxuan-jinghua` / 各类 `*-perspective` | 经典/名人思维框架蒸馏与引用（毛选已 229 篇双校验） |

---

## 📌 通用铁律（跨场景，先于一切技能）
- **回源纪律**：输出引文/数据/名单/配置值前必须回源核对（技能 `ground-truth-discipline`），禁用记忆补全；数字类说法尤其易错。
- **造轮子前先查**：`find-skills-xiaoka` → 本地 `ls skills | grep 关键词` → GitHub（技能 `find-skills-xiaoka`）。
- **出网受限**：curl 常超时，优先 `web_search`+`web_extract`；经典文本找 GitHub 开源仓（git 协议通、HTTP 常被墙）。
- **写文件边界**：write_file/patch 只能写 `/opt/data`，改 NAS/vault 走 SSH 到 NAS 的 root docker 容器（见记忆）。
- **不抢前台**：任何 CDP 浏览器操作 background 建标签、不 bringToFront、最多 2 个抖音标签。
