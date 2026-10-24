# 蜂群 Agent open_id 汇总报告

生成时间：2026-10-19 09:30 (UTC+8)
维护者：星期五-新Hermes (QUEEN)
原始台账：/home/agentuser/swarm_oid_ledger.json

## ⚠️ 核心规则（必读）

1. **open_id 是应用维度的**：同一个用户/群在不同飞书 app 下 open_id 完全不同
2. **@ 对方必须用「自己 app 视角下对方的 sender id」**（即自己收到的消息里的 id）
3. 自报的 open_id 仅作节点身份声明，**不能直接拿来跨 app @**
4. 群会话 chat_id 是租户维度的，跨 app 一致：管理群 = `oc_568730200f9a3120919be177344687e5`

## 一、星期五 app 视角（QUEEN 可直接 @ 的 id）

| 节点 | open_id (星期五视角) | 角色 |
|------|---------------------|------|
| 星期五-新Hermes (QUEEN/我) | ou_cec7da8fb7c87ba06dcb4b2110c9ede1 | 云端调度/通信枢纽 |
| 小豆-新Hermes | ou_3501ce1fe1ab90a9c94fc232db1927dd（星期五视角）／ou_4b8b06fc47ac1a6372bae51f01aebbd4（小卡视角） | 小豆-新Hermes = **另一朵云的全新 VPS（IP 未知，待小豆自报）**，Hermes default profile、工作区 `/home/agentuser/A2A`；**旧 Mac 端小豆已停用作废**（旧址 `/Volumes/2-AI/A2A`、`launchd ai.hermes.gateway`），两者无关。⚠️ `100.66.1.6` 是**星期五/Queen** 的云端 VM，不是小豆，配置/流量别串台 |
| 小米-codex (蜂王) | ou_fc604d3323ba024e2400db900df3a008 | Mac 端编排/SRE |
| 小丽-workbuddy | ou_a894c95f3540f53997cf14292a664db7 | 美客多业务线 |
| 小丽2号-workbuddy国际版 | ou_2ae7b9213c69801aa7dcdf8bf05f70e0 | Mac 国际版 |
| 小七-workbudd-windows | ou_25581717b63c2c9877a550678065251d | Windows 执行节点 |
| 阿正-workbuddy-win国际版 | ou_409f36a339b1938c47d8dfe7fbf283b5 | Windows 国际版 |
| 小卡-nas | ou_5b83d86fd6a3df488943f7d0f86875cf | NAS/Gitea/SRE |
| 贾维斯-XF | ou_f41df1b511fd938330bcf92bcf0ed09c | 编排/派单/验收 |
| 雷神-XF | ou_f47c031ffd8af235c3d0a19e3d8d2a7a | BOSS 侧助理(新) |
| 绿巨人-XF | ou_1229c9d17f82256204f07c80d928efe1 | 本地 Claw 执行(新) |
| 徐先生 (BOSS/用户) | ou_138ca8b3b84e482b5ed04b98841f7c77 | 人类指挥官 |

## 二、各节点本 app 视角（自报身份声明）

| 节点 | 本app open_id | app_id | 机器/角色 |
|------|--------------|--------|----------|
| 星期五 | ou_cec7da8fb7c87ba06dcb4b2110c9ede1 | cli_aa29ff4a46b81d2b | 云端 VM Linux |
| 小卡-nas | ou_7911620a998eba218db4a0670d21651f | cli_aa019ce718b8dbeb | 绿联 NAS |
| 贾维斯 | ou_8c1cb7f9dbb2370b6c04d9149415ecd6 | cli_aa0b6efaf8b89bb4 | 云端/Linux |
| 小七 | ou_3c1c0ac49dc1fa74f911a2f32ac98736 | cli_aa48c427a8f8dcc2 | Windows 执行 |
| 雷神-XF | ou_29d57e6def307f7cb4cfe4d3c774eeda | cli_aa5e69549d381c1e | Win10 国内版 WorkBuddy |
| 绿巨人-XF | ou_e9cf64fed191b71ca37900f15ebeb832 | cli_aa5e72e517f85c10 | Windows WorkBuddy Claw |

## 三、跨 app 映射样本（证明应用维度）

| 视角 | 看到的对象 | open_id |
|------|-----------|---------|
| 绿巨人视角 | 星期五(QUEEN) | ou_9dae5f162d12cd5c8f213befb6db7ff2 |
| 绿巨人视角 | 另一操作者 | ou_3414fc3a6f036b5b7888f26d1f5e73ec |
| 雷神视角 | 星期五(QUEEN) | ou_defad7365337611f5fe2fca0e827d85f (已确认) |
| 雷神视角 | BOSS(推断待确认) | ou_ffd716eb86df6a01295f29dd20305c8c |

## 四、跨 app 对齐方法

需要跨 app 稳定识别时用 union_id（on_ 开头，开发者维度）：
- 管理群 session 样例: agent:main:feishu:group:oc_568730200f9a3120919be177344687e5:on_7fe4e470...
- 各 app 需在同开发者主体下才能互换 union_id

## 五、通信链路现状 (2026-10-19)

- ✅ 飞书群 @ 双向：11 节点台账齐，QUEEN 出站 8/8 验证
- ✅ A2A 总线 (GitHub superxzy2012/a2a-bus)：全通，cron */5，冲突兜底已加
- ✅ 云端→NAS MCP：100.66.1.7:3456 (obsidian) / :3458 (skillbox) 全 200
- ⏳ 雷神/绿巨人总线接入：SMOKE 任务已投递，等回执

## 小豆-新Hermes 网络自报（2026-10-21，待核实）
- 云端 VPS 公网 43.153.26.131（腾讯云段），内网 10.4.4.16/网关10.4.4.1
- 主机名 10_4_4_16，用户 Administrator，sshd 22 仅密钥
- NodeBabyLinkService v4.3.5 已装（精简版，wintun 就绪），异地组网 IP 未分配
- 请求：小卡用 BOSS 的节点小宝账号点绑定链接 + 给小卡 pubkey
- 状态：**未执行**。等 BOSS 授权（涉私有组网边界 + 需 BOSS 账号）

## 2026-10-23 QUEEN open_id 交叉核对
- 小卡本 app 实测收到 QUEEN/星期五 的 sender：`ou_b172b28aa8416f7fca826bc151b9cbb8`（gateway.log 14:42:36 原文，sender=bot:ou_b172...）
- QUEEN 自报 `ou_cec7da8fb7c87ba06dcb4b2110c9ede1`：**作为 `<at user_id>` 输入可用**，飞书会自动 canonicalize 成 `ou_b172b28aa8416f7fca826bc151b9cbb8`（2026-10-23 实测：两个 id 同时 @，mentions 两项 id 都回落 ou_b172...，tenant 1acb5ce38507dc9e）。身份比对/白名单仍用实测值，@ 用哪个都行。
- 我读不到群历史（230027 缺 im:message.group_msg），群内 @ 关系只能靠 gateway.log 事件流 + 总线
