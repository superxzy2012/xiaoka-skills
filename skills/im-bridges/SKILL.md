---
name: im-bridges
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [im, bridge, whatsapp, feishu, nextbridge]
    related_skills: [feishu-group-bot-bridge, feishu-bot-group-mentions]
description: Use when 搭建/排障 IM 桥接（NextBridge）或 WhatsApp 扫码配对。
---

# IM 平台桥接（NextBridge / WhatsApp 配对）

NextBridge：多 IM 平台双向桥接框架（Python，`drivers/` 每平台一个驱动：飞书/WhatsApp/Telegram/Slack 等二十多个；登录态存 sqlite DB）。WhatsApp 协议层用 neonize（whatsmeow 的 Python 绑定，二维码/配对码登录）。源码快照在 /opt/data/cache/scratch/NextBridge。

## When to Use

触发：搭建/重启/排障 NextBridge 桥接（飞书↔WhatsApp/Telegram 等）、做 WhatsApp 扫码配对、或用户报告「扫码了但桥没通」。

## 铁律
- 给用户二维码前必须确认：①配对进程还活着（ps 核对 pid）；②这张码是**当前活着的进程本轮**生成的。WhatsApp 配对码几十秒就过期，进程死了扫了也白扫——用户扫「死码」是最浪费的一次往返。
- 连 WhatsApp 必须走 mihomo 代理 192.168.199.2:7891（HTTPS_PROXY/HTTP_PROXY/ALL_PROXY 一起设）。直连不是报错而是**静默挂起**：进程活着、无输出、无异常，靠「20 秒还等不到 QREv」判断卡住，不要等报错。
- 配对成功以日志出现 `CONNECTED-EVENT` + `LOGIN-PERSISTED` 为准，看到之前不许向用户报「已连上」。登录态持久化在 `NewAClient(DB)` 的 DB 文件里，重启进程直接复连不再出码；DB 丢了就要重新扫码。
- 沙箱容器里 docker 只有 CLI、没有守护进程（无 /var/run/docker.sock，dockerd 也未安装），NextBridge 容器跑不起来。沙箱内只做配对/验证（neonize 直接跑 venv）；常驻桥接进程放 NAS 或宿主机。

## 步骤（沙箱内做 WhatsApp 配对）
1. 环境：`neonize` + `segno` 装进 /opt/data/.venv-browser（pip 走清华源）。neonize import 时要加载 libmagic，沙箱无 root 装不了 apt 包——跑 scripts/ensure_libmagic.sh 从清华镜像下 deb 解包到 /opt/data/local/libmagic。
2. 后台启动 scripts/wa_pair_local.py（terminal background=true，日志重定向到文件）：它监听 QREv 生成二维码 PNG + 终端 QR，收到 ConnectedEv 后保持心跳。约 20 秒内出码。
3. 若日志里只有终端 QR 没有 PNG（segno 异常），用 scripts/render_terminal_qr.py <日志文件> <输出.png> 把终端块字符码转成 PNG，用 MEDIA: 发给用户。
4. 用户扫码后核对日志出现 `PAIR-STATUS` → `CONNECTED-EVENT` → `LOGIN-PERSISTED`，确认后才算配对成功；然后再把 DB 路径接进 NextBridge 的 drivers/whatsapp.py 常驻运行。

坑：无 ffmpeg 时 neonize 只告警不致命（贴纸/语音/视频/缩略图等媒体操作会失败），纯文本桥接可忽略。
