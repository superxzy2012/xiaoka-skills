---
name: muse-wa-bridge
description: Use when 排障/重启/改配飞书↔WhatsApp 桥接（NextBridge+neonize）。
---

# muse-wa-bridge 飞书↔WhatsApp 桥接

## 架构与路径
- 桥接程序：NextBridge v0.3.0，`/opt/data/cache/scratch/NextBridge`（siiway/NextBridge 上游 + xiaoka 改过 whatsapp.py 的 QR 日志）
- 启动：`bash /opt/data/cache/scratch/muse_wa/run_bridge.sh`（后台常驻；内含 mihomo 代理 + LD_LIBRARY_PATH + NEXTBRIDGE_DATA_PATH）
- 运行日志：`/opt/data/cache/scratch/muse_wa/bridge_live.log`（在线状态、抓 JID/chat_id 都看这里）
- 配置：`NextBridge/data/config.json`（global.proxy=192.168.199.2:7891；feishu.fs_muse；whatsapp.wa_muse）
- WhatsApp 登录态：`NextBridge/data/wa_muse.db`（账号 86【手机号】，已配对「Safari (Neonize)」，重启免扫码）
- 飞书凭据备份：`/opt/data/cache/scratch/muse_wa/secrets/feishu_fs_muse.env`（600；app_id=cli_aa56719d6178dcf1，secret 曾在聊天里出现过，建议 BOSS 重置）
- 飞书目标会话：chat_id=`oc_440d948afcceaac57e2ac1e6144e6f05`（fs_muse 机器人与 BOSS 的单聊）
- 配对脚本：`wa_paircode.py`（8位配对码登录）、`render_qr2.py`（终端二维码转 PNG）

## 现状（本实例已打通的部分）
- `rules.json` 已配：`type=connect`，`wa_muse.chat_id=【手机号】47697@bot` ↔ `fs_muse.chat_id=oc_440d948afcceaac57e2ac1e6144e6f05`。改规则后**必须重启进程**，本版没有 SIGHUP 热加载。
- 正向（飞书 → WhatsApp）已验证：`on_message` → `Dispatching to wa_muse` → `send_message` 返回消息 ID，手机端可见。
- 反向（WhatsApp → 飞书）当时未通：MUSE 是 Meta AI 认证 bot，回复走 `protocolMessage{MESSAGE_EDIT}` 富响应，驱动默认消息类型分支全部落空。结构、抽取函数与探针补丁见技能 `whatsapp-bridge-ops` 的 `references/whatsapp-inbound-message-types.md` —— **同类内容以那份为准，别在这里重复摸索**。

## 硬坑（每条都真踩过）
1. **同一 WhatsApp db 绝不能两个进程同时 connect**——WhatsApp 会 StreamReplaced 互踢，桥接静默掉线（表现为「发了消息桥接没收到」）。跑任何 neonize 诊断脚本前先杀 main.py。
2. **WhatsApp 必须走代理** 192.168.199.2:7891，直连被墙卡死无报错（进程活着但 QR 永远不来）。
3. **扫码登录不可行**：二维码几十秒过期，飞书传图到手机就死了。用 8 位配对码：`client.event.qr(callback)`（注意不是 @client.event(QREv) 装饰器——那个不触发），回调里 `await client.PairPhone("86【手机号】", True)` 拿码，手机「关联设备→用手机号码关联」输入。
4. **libmagic**：沙箱无 libmagic1 且无 root，借位包在 `/opt/data/local/libmagic/`，跑 neonize 必须 `LD_LIBRARY_PATH=/opt/data/local/libmagic/usr/lib/x86_64-linux-gnu`。
5. neonize 装在 `/opt/data/.venv-browser`（uv 无、pip 可用，清华源）；系统依赖按 pyproject 补装过 fastapi/uvicorn/lark-oapi/sqlalchemy 等。
6. Docker 方案已废弃：沙箱 dockerd 不可用，昨晚的容器和数据卷（含旧 config.json）已丢，现全部本地裸跑。
7. 终端打 QR 是「亮块深底」反色，转 PNG 用 render_qr2.py（黑块白底才可扫）。
