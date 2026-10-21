---
title: "浙大开源 nanoMuse：把个人 Agent 装进手机/电脑/浏览器，Meta Muse 的开源平替"
source_url: "https://v.douyin.com/vUZ-p1ZRylk/"
platform: douyin
douyin_id: "7698690965183188265"
author: "哈工大AI 工程师 Peter"
duration: 119.746s
date: 2026-10-20
github_repo: nano-muse/nanoMuse
license: GPL-3.0-or-later
tags: [抖音, 个人Agent, nanoMuse, 浙大, 开源, Docker, 已实测]
added_by: 小卡
status: 已核查
---

# 浙大开源 nanoMuse：把个人 Agent 装进手机/电脑/浏览器

**一句话**：nanoMuse 是浙江大学团队 2026-09 开源的「跨设备个人 Agent」——手机 App、桌面端、网页控制台 + 一个中继 Hub，一套账号一段对话，Agent 在你的设备本地跑，GPL-3.0。**它和 Hermes 高度重叠但不重叠完**：同样的工具/MCP/技能/飞书入口它都有，缺的是多 agent 蜂群、A2A 总线、服务器侧运维深度；它多出来的是**用屏幕操作手机 App 和电脑窗口的那双手（Hands）**。

> 🎬 抖音 · 哈工大AI 工程师 Peter · 119.7 秒 · 2026-10-20 入库 · 2026-10-21 全篇重写并实测

## ✅ 回源核查（GitHub API / README / arXiv，2026-10-21）

| 项 | 实测值 | 结论 |
|---|---|---|
| 仓库 | `nano-muse/nanoMuse` | ✅ |
| Star / Fork | **1,639** / 184 | ✅ 建库 4 周，涨得快，视频说「掌心非常之快」成立 |
| 建库 / 最近推送 | 2026-09-23 / 2026-10-20 | ✅ 极早期但仍在高频迭代 |
| 许可证 | **GPL-3.0-or-later**（基于 OpenMinis 1.13，GPL-3.0） | ✅ 视频说 GPL-3.0 准确 |
| 最新版本 | **v1.0.5**（2026-10-13），15 个产物 | ✅ |
| 主语言 | Swift（App 层）；内核是 Python 包 `nanomuse` | — |
| 作者单位 | Guangyi Liu、Yong Liu、Jiangning Zhang —— **浙江大学** | ✅ 「浙大开源」成立 |
| 论文 | arXiv **2610.08699** | ✅ |
| 官网 / Demo | nanomuse.cn / demo.nanomuse.dev | ✅ |
| Open Issues | 65 | ⚠️ 4 周 65 个待办，早期项目特征 |

> 视频里「**这大**团队」是 ASR 把「**浙大**」听错，已在正文更正。

## 🖥️ 我实测装了什么（不是看 README，是真跑）

在 NAS（192.168.199.2）用官方 Dockerfile 构建并起了服务器侧：

```bash
cd /volume2/2-AI/nanomuse
sudo -n docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple -t nanomuse:latest .
sudo -n docker run -d --name nanomuse-app --env-file .env -p 8787:8787 \
  -v nanomuse-data:/data -v .../workspace:/workspace \
  -v .../config/config.toml:/app/config/config.toml:ro \
  nanomuse:latest serve --host 0.0.0.0 --no-qr
```

**验证结果（都是真实输出）**：

| 检查 | 结果 |
|---|---|
| 镜像 | `nanomuse:latest` 391 MB，构建成功 |
| 容器 | `Up (healthy)`，`0.0.0.0:8787->8787` |
| Web 控制台 | `HTTP 200`，1,899 字节；带 token 打开后渲染出「Meet your nanoMuse」引导页 |
| 真跑一次模型 | `docker exec nanomuse-app nanomuse run "..."` → 正常返回中文自我介绍，走的是本机 OmniRoute `a2a/deepseek-v4.1-flash` |
| 落点 | `/volume2/2-AI/nanomuse`（源码+config+workspace），`.env` 600 |

**踩到的坑（已修）**：默认模型 id 写 `deepseek-v4.1-flash` 直连 OmniRoute 会 **404**，必须用带前缀的 `a2a/deepseek-v4.1-flash`。改 `config/config.toml` 的 `[llm].model` 后重启容器即通。

## 💡 它到底能干什么（README 原文归纳）

1. **会动手**：内置 Linux shell、浏览器、MCP servers 和 skills；打开「Hands」后还能通过**屏幕**操作手机 App 和电脑窗口——给那些永远不会有 API 的东西用。
2. **会先问**：独立的 Sentinel 审每一步，删除/发送/付款会停下来等你确认；密钥放 vault，模型读不到。
3. **会记事**：有自己的名字和形象，跨设备共享同一账号、同一段对话；手机/桌面/网页可以互相「接力」办事。
4. **模型自选**：任何 OpenAI 兼容端点；社区 relay 送一段免费额度，用完自带 key。
5. **能自托管**：仓库里有 Dockerfile + docker-compose（`app` 8787 / `daemon` 定时推进目标 / `muse` 终端聊天）。

## ⚠️ 视频漏说的五件事

| 视频观感 | 实际情况 |
|---|---|
| 「低成本平替，免费」 | 社区 relay 的免费额度是**开发者自掏腰包**，用完必须自带 API key。低成本≠免费 |
| 「一键部署到所有场景」 | 每个平台一个安装包；服务器侧才是一行 docker。iOS 只有 **TestFlight 内测**，macOS **未公证**（首次要右键打开），Android 仅 **arm64** |
| 「开源，随便用」 | **GPL-3.0-or-later**：分发衍生品必须开源。想闭源包装成商品卖——不行 |
| 「替代所有个人 Agent」 | 定位是「长在设备上的 App」。**飞书/钉钉/企业微信/Telegram 入口它其实有**（`nanomuse[channels]`，走长连接，扫码建 bot），但**没有多 agent 蜂群、没有 A2A 总线、没有跨机器运维深度**——那些是 Hermes 的活 |
| 「GitHub 日榜第 7」 | 这句来自抖音自动摘要，不是口播；GitHub 无公开日榜 API，**无法核实**，只能存疑 |

## 🧭 对小卡/BOSS 的实际价值

- **能用的场景**：BOSS 想在**手机**上有个能自己动手的 Agent（点 App、读屏、跨设备接力），nanoMuse 是目前最完整的一个，而且已经在我们 NAS 上跑起来了。
- **不能替代的**：我现在这套（服务器常驻 + cron + 飞书群 + 多 bot 协作 + 知识库入库）nanoMuse 都没有，别拿它换掉 Hermes。
- **商用红线**：GPL-3.0，任何对外分发的衍生产品都要开源；只自己用没问题。
- **下一步（可选）**：① 手机装 APK 连 NAS 这个 relay；② 开 `WITH_BROWSER=1` 重建镜像给容器装浏览器手；③ 或者直接当技术参考，看它怎么把 Sentinel 审批做进每一步。

## 📝 转录原文（ASR，未逐字校对）

各位这大团队刚刚开源了它的超级个人智能体nanomuse 我觉得这款工具太适合我了我觉得特别适合在屏幕前的每一位同学和朋友它足够轻足够小而且是一套五脏俱全的解决方案能部署到你的手机周面APP网页控制端所有的地方你只需要把它一键就可以部署到你所有的场景当中然后目前这款工具我就在全网非常火就是可以自信化可以持续学习然后以一个非常低成本的评替可以替代所有的个人agent就是大家知道目前千万豆包都在抢先想要去做personal assistant的就是个人的AI助理AI助手的这种工具我觉得在这个基础之上做一些二次开发它就可以真正成为你的数据员工然后去服务于你所有的生活场景和个人场景当中然后给大家看一下它整个的GitHub的掌心非常之快然后它到底能做什么第一个就是它具有一个云端的环境然后能够主动的去找到问题发现问题并且记住你是谁然后你可以赋予它相应的形象它可以部署在所有的场景当中去完成相应的解决方案哇那这个太厉害了也就是说它可以在多平台之间进行相应的协作然后最后把你的任务全部完成倒吸一口凉气真的就是设备上都跑起来整个的这套解决方案然后他自己也做了一个它和MetaMuse相应的一个对比首先第一个MetaMuse是跑到云端的它相应的整个的成本会更高但是NanoMuse就是这大传统团队开源的这个方案它可以在你的每一个服务器和场景当中就真实在你的场景当中然后最后的审批权控制权在你自己的手上第二个就是它是开源的它不像MetaMuse是B源的一个产品然后也就意味着你可以把你自己的API Key或者是你自己的一些场景和解决方案比如说你想要自己做一些MCP你想要自己做一些插件或者是Plugins一些东西都可以自己接进去可以定制你自己的个人助理大家明白吗一键部署 我觉得这个工具真的太适合所有人用了那么当下很多人在讨论到底 ai 助手或者 ai 个人助理到底是不是一个生意逻辑这件事情到底是不是一个有机会的市场和有商业价值的市场但我认为这件事情无比有意义 未来我相信2027年开始所有应用端 所有 app 所有场景的入口唯一的入口会变成个人助理AI agent和个人 AI assistant

> 校正记录：「这大团队」→「浙大团队」；「周面」→「桌面」；「自信化」→「自进化」；「评替」→「平替」；「掌心」→「涨星」；「B源」→「闭源」；「千万豆包」应为「千问、豆包」。

## 🔗 相关

- 仓库：https://github.com/nano-muse/nanoMuse
- 论文：https://arxiv.org/abs/2610.08699
- 本机部署：NAS `192.168.199.2:8787`（容器 `nanomuse-app`，配置 `/volume2/2-AI/nanomuse/config/config.toml`）
