# Muse 渠道集成方案对比（飞书 / WhatsApp 桥接）

给「想在飞书/WhatsApp 里聊 Muse」的需求选型用。先看风险铁律，再看方案表。

## 风险铁律
- 逆向网页接口做 API 的项目（muse2api 类）**禁用**：多账号池轮转 + 自动续期是典型封号行为，且 cookie 交给第三方网关。BOSS 账号是高价值资产，任何方案不得把它暴露给这类网关。
- 任何「官方 WhatsApp 个人号自动化」库（whatsmeow/neonize/whatsapp-web.js/Baileys）都违反 WhatsApp 条款，封的是 **WhatsApp 号**不是 Muse——只准用专门的小号，绝不能挂 BOSS 主号。
- 非官方不等于立刻封：muse-cli 类单账号、低频、行为与真人客户端一致的用法风险低一个量级，但不能向用户承诺「100% 不封」。
- 登录本身不是封号风险：同国家换 IP 只触发一次邮箱验证码；别跨国来回跳节点。真正封号的是账号池、接口滥用、邀请码刷量。

## 方案对比

| 方案 | 链路 | Muse 账号风险 | 备注 |
|---|---|---|---|
| muse2api | 逆向网页接口→OpenAI 兼容 API | 极高 | 禁用 |
| muse-cli 直连桥 | 飞书 bot→本地 muse-cli（官方客户端同款协议，cookie 取自本机 Chrome） | 低～中 | github.com/nikships/muse-cli；桥本身与 Codex 接飞书同架构，风险全在 CLI 端；单账号+限速+只私聊 |
| 官方 WhatsApp | Muse Settings → Messaging channels → WhatsApp（**扫码配对**，不是填号/wa.me） | 零 | 唯一官方消息渠道（Connectors 列表里没有飞书/Lark）；门槛：一台已登录 WhatsApp 的**手机**去扫二维码，+86 号段短信不可靠 |
| WhatsApp 做中间人（飞书→WhatsApp→Muse） | 飞书 bot→桥→WhatsApp→Muse | Muse 侧零，风险全在 WhatsApp 一跳 | 现成轮子 NextBridge/matterbridge/WuKongBot 的 WhatsApp 一跳全是非官方协议；全官方链只有 WhatsApp Cloud API（需专用号+Meta Business 注册，Muse 能否绑定 Cloud API 号未验证，全网无案例） |
| 自建 agent（nanoMuse 飞书频道） | 飞书 bot→OmniRoute 模型 | 零（不碰 muse.ai） | 不是 Muse 本体，不消耗领的 token；飞书 app 不能与 Hermes 共用（长连接互抢） |

## 部署位置：云浏览器不是服务器
Hyperbrowser 云浏览器是**一次性会话**（Linux + Chrome 桌面）：不开放入站端口、IP 每次变、连接一断就回收，装不了常驻服务。所以「7×24 跑的桥」只能落在 NAS 容器里，云浏览器仅用于一次性的人工注册/绑定操作。BOSS 问过「能不能开端口给我们维护」——答案是不能，维护点在 NAS。

## WhatsApp Cloud API 的门槛（选型时先讲清）
- 需要一个**专门注册给 Meta 的号码**，注册后该号不能再登个人版 WhatsApp；国内副卡能收短信即可试，Google Voice 类虚拟号大概率被拒。
- 个人用量基本落在每月免费对话额度内（约 1000 次/月），超出一两美元级。
- 有 **24 小时对话窗口**：用户发起后 24h 内可自由回复；超窗要先发审批过的模板消息。
- 未验证项：Muse 的 Messaging channels 是否接受 Cloud API 号绑定——全网无案例，必须先实测。

## 绑定机制（已实测，别再猜）
Settings → Messaging channels 里**只有 WhatsApp 一个渠道**，点进去是**扫码绑定**：用手机 WhatsApp 扫描页面二维码，Muse 即以「已配对会话」形态接入。没有填号入口、没有 wa.me 预置消息、没有 API key。

推论（选型必读）：
- 门槛是**一台已登录 WhatsApp 的手机**，不是「能收短信的号码」；+86 号段短信投递成功率低，实际要走国际号或虚拟号。
- 桥替代不了这次扫码：桥（whatsmeow/neonize 类）只能以同一账号的**另一个 linked device** 身份配对，去读 Muse 那条会话再转发到飞书。所以顺序固定为「先有可用 WhatsApp 号 → 扫码绑 Muse → 再挂桥」。
- Muse 侧因为是官方配对，Muse 账号零风险；封号风险全部落在 WhatsApp 号上，必须用小号。
- 绑定形态会改版：写教程/选型前重新点一遍确认，旧文档里「wa.me 跳转」的说法已不成立。

## 名字澄清（防误装）
- 「飞书 CLI」= 飞书官方 feishu-cli（操作飞书文档/消息），与 Muse 无关，不能用来接 Muse。
- GitHub 的 MuseBot（yincongcyincong，Go）名字蹭 Muse，实际接 DeepSeek/OpenAI 等做飞书 bot——想要飞书 AI bot 但不要 Muse 时可用。
- awesome-muse-connectors 目录里没有飞书/WhatsApp 桥接方案，别再重复翻。