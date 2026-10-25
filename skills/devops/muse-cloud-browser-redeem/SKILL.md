---
name: muse-cloud-browser-redeem
description: Use when 在 muse.ai 登录或兑换邀请码领 token。
version: 1.0.0
author: 小卡
license: MIT
metadata:
  hermes:
    tags: [muse, hyperbrowser, cloud-browser, invite-code, automation]
    related_skills: [hyperbrowser-cloud-browser]
---

# muse.ai 登录 / 邀请码兑换（本机 Chrome 优先，云浏览器兜底）

## When to Use
- 用户要在 https://muse.ai 登录、兑换邀请码/Referral 领 token。
- 必须美/加 IP：用 Hyperbrowser（api.hyperbrowser.ai）美国区会话，`useProxy:false,useStealth:true,adblock:true,profileId:<持久档案>`。

## 通道选择：优先 BOSS 本机 Windows Chrome（9223）
账号登录过一次之后，**默认用 BOSS 本机 Chrome（CDP 9223），不要再用 Hyperbrowser 云浏览器**：
- 本机 Chrome 的 cookie 存在用户配置里，登录一次长期有效，不用反复要验证码；云浏览器 profileId **不保存 Muse 登录态**（实测）。
- 本机是真实桌面浏览器指纹，比机房 IP 云主机更不像机器人；session 也不会因脚本退出被回收，可以分多次工具调用慢慢操作。
- **前提：该 Chrome 出口必须是美国**。动手前先实测——后台标签开 `https://ipinfo.io/json?r=<随机数>`（带随机参数绕缓存），读 `country`。读到 `CN` 说明梯子只挂了别的程序、浏览器没走代理，此时登 Muse 必被拦，先让用户把系统代理/扩展打开。
- 登录步骤（Playwright `connect_over_cdp("http://127.0.0.1:9223")`，后台标签，不抢焦点）：填 `superxzy2013@gmail.com` → 点「继续」→ 用户报最新 6 位码 → `input[autocomplete="one-time-code"]` 先 `focus()` 再 `keyboard.type(code, delay=250)` → 勾「记住此设备」。
- **Muse 界面会跟随浏览器语言变成中文**：按钮是「继续」「下一步」「设置」「消息渠道」。英文 `get_by_role(name="Continue")` 匹配数为 0，看起来像按钮不存在。选择器一律中英双语兜底。

## 核心事实（2026-10-24 实测，账号 superxzy2013@gmail.com）
- 新账号注册起 **48 小时内**必须兑换，超时入口消失。注册时间看最早一批 scratch 日志。
- 登录是**邮箱 6 位验证码**（无密码）。验证码 TTL 短，且每次触发发新码会使旧码失效——**只认最新一封邮件**，多封并发一定用最新那封。
- 带已登录 profileId 开新 session 访问 `/join`，会直接 302 到主界面（`/?aymh_complete=1`）——登录态在时别把跳转后的落地页误判成注册页没打开。
- 国内直连 muse.ai 是**连接超时**（CDP Page.navigate 都会 30s 超时断连），不只是页面提示地区受限——给教程写「为什么需要美国环境」时用这条实证。
- **Hyperbrowser 持久档案(profileId)不保存 muse 登录态**：每次新会话都要重新要验证码。不要假设 cookie 还在。
- **一个 session 只允许一个 CDP 连接**：保活脚本占着时，第二个 connect_over_cdp 会把会话挤成 closed。要「保活+调试」就得写在**同一个脚本/同一条连接**里，别开第二个连接。
- **会话与那条 CDP 连接同生共死**：连接一断（脚本正常退出、被 kill、异常）session 立刻不可用，`connect_over_cdp` 重连必报 404 `session not found`，等几分钟也不恢复。所以「发码→登录→导航→操作」全部写进**一个脚本**，用动作文件在连接内驱动（见「脚本工程纪律·单连接驱动模式」），**不要 kill 后换脚本重连**——那样既丢登录态，又白烧用户一个验证码。

## 查本人邀请码与推荐链接（邀请别人时）
- 路径与兑换同源：登录 → 左下三横线 → 顶部 **Invite**（或设置里的邀请区块）打开 **Invite friends** 弹窗 → 点 **Copy referral link**。
- 弹窗刮刮卡显示的 6 位码就是**登录者本人的码**；「Invite friends」页和「Redeem invite code」是两件事，替人领奖励走 Redeem，分享自己的码走 Invite，写文章前必须分清两者，张冠李戴等于给别人做嫁衣。
- 推荐链接别靠读剪贴板取（无头云浏览器 clipboard 常读不到，空字符串），直接在登录页面里 `fetch('https://muse.ai/api/hatch/invite',{method:'POST',credentials:'include'})`，返回 `{code, max_uses, use_count, invite_link}`，权威且带剩余名额。
- **官方 invite_link 是不带任何专属参数的通用落地页（https://muse.ai/join）**：点链接不绑定邀请关系，被邀请人仍必须手动填码。宣传文案里不要编带参的「专属链接」，正确表达是「链接跳转 + 注册后填码，缺一不可」。

## 登录页与设置入口的实测细节（1280x900 视口）
- 验证码输入框是 `input[autocomplete="one-time-code"]`、`class="sr-only"`，六个可视格子只是装饰：**`locator.click()` 必超时**，报 `<div class="w-full" role="presentation"> intercepts pointer events`。正确做法：`.focus()`（失败则 `eval_on_selector(el=>el.focus())`）→ `keyboard.type(code, delay=300)` → 读 `el.value` 核对 → `keyboard.press("Enter")` 提交。别用坐标点格子。
- 设置入口是**左下角齿轮**（英文 `aria-label="Settings"`、中文界面 `aria-label="设置"`；1280x900 下中心 ≈ (36,868)；1280x720 下是三横线 ≈ (40,605)，UI 版本不同位置不同，先 dump 控件坐标再点）。点它弹出的是**浮层菜单**（英文 Keyboard shortcuts / Download apps / Report an issue / Settings；中文 键盘快捷键 / 下载应用 / 报告问题 / 设置），**不会直接打开设置面板**。
- 浮层菜单项是普通 div，**不在 `button,[role=button],a` 里**：按标签枚举控件完全抓不到它们。云浏览器后台标签里坐标盲点连点 6 次都进不去；**BOSS 本机 Chrome 里 `get_by_text('设置', exact=True).click(force=True)` 一次成功**——差别在云浏览器后台标签不做真实命中测试。命中后先验证 body 文本里出现设置项（通用 / 消息渠道 等）再继续。
- 本机 Chrome 里设置是标准弹窗（`[role=dialog]`，1440x900 下 ≈ x320,y150,800x600），左侧导航坐标：通用 (352,226)、连接器 262、钱包 298、安全存储 334、权限 370、**消息渠道 (352,406)**、设备 442、数据控制 478、帮助与支持 514、法律信息 550、退出 718。
- 进设置后左侧导航才有 General / Connectors / Wallet / Secure store / Permissions / **Messaging channels** / Devices / Data controls / Help & support / Legal info / Log out。

## 兑换路径（坐标基于 1280x720 美区页面）
1. 左下三横线菜单：`mouse.click(40,605)`（不是聊天消息上那些 x=200 的 More options）。
2. 弹出菜单点 Settings：用 `get_by_text('Settings',exact=True)` 取 `bounding_box().x<260` 的可见项（实测在 ~120,592 / 菜单在 ~201,602）。**别用模糊文本**，否则点到聊天区同名文本，设置窗根本不开。
3. 设置窗左侧导航：General / Connectors / Wallet / Secure store / Permissions / Messaging channels / Devices / Data controls / Help & support / Legal info / Log out。
4. 兑换入口在 **General 页**，Usage/Free plan/Upgrade 下面一行 **「Redeem invite code」**（英文界面本来就有，不用切语言；点它前在 body 文本里确认该串存在）。
5. 弹出「Redeem a code」弹窗，说明：Redeem a friend's code within 48 hours... both get 1 billion Muse tokens。

## 六格分立式输入框（最大坑）
- 邀请码框是**六个独立小格**（一格一字，类似短信验证码），**不能用 `fill(整串)`**——会被透明层拦、报 Locator.click timeout。
- 正确做法：`first.focus()` 第一个可见文本 input → `keyboard.type('O0WKS9', delay=180)`（键盘事件自动逐格跳）→ 读六个 input 的 input_value 拼起来核对。
- 提交：**Confirm 按钮**（蓝色，实测中心 ~641,527），`mouse.click(641,527)`；若弹窗还在再用 `button:has-text('Confirm')` 补点。

## 成功判据
- 点 Confirm 后弹窗**不关闭**，而是变成祝贺页，原文：
  **「Congratulations! Your code redemption was successful. You both got 1 billion Muse tokens.」**
- 判定成功要看是否出现 `Congratulations`/`redemption was successful`，**不要**用「弹窗关闭」当判据（会误判 False），也别把弹窗说明文案里的 `1 billion` 当成功信号（没兑换时文案里就有）。失败文案：invalid/incorrect/expired/already。

## 脚本工程纪律（血泪）
- 全程 `screenshot(timeout=20000)` 且**包 try，失败只 log 不抛**——设置弹窗打开时截图常超时，一旦异常冒泡进程就死、会话被回收、又得要一次验证码。
- `inner_text('body')` 包一个重试 helper（domcontentloaded 后 4 次重试），导航瞬间超时别让脚本崩。
- **千万别写 `time.sleep=.5` 这种手误**（会把 time.sleep 覆盖成 float，后续所有 sleep 报 'float' object is not callable）。
- Playwright Python：自定义 `eval_on_selector_all` 传参时，页内 JS 拿到的参数是值，别在回调里对非字符串调 toLowerCase（TypeError: txt.toLowerCase is not a function）。优先用 Playwright 原生 get_by_text + bounding_box 过滤，少写自定义 JS。
- 等验证码：轮询码文件（每 5s），脚本启动前先删旧码文件；码文件用 `printf '码' > file` 写入，写完脚本可能延迟 1-2 轮(≤15s)才读到，正常，别急着重启。
- **单连接驱动模式**（会话不能重连时的唯一正确做法）：保活脚本里加一个动作循环——每 3s 读 `nav_action.txt`，支持 `clickxy x y` / `clicktext 文本` / `clicklabel aria` / `esc` 几个分支，每步后截图（包 try）+ 把 `button,[role=button],a` 的 `{t,al,x,y}` dump 到 `controls.json` + 结果写 `nav_out.txt`，就能在**不重连**的前提下远程点页面。
- 写动作分支时 `pg.wait_for_timeout=3000`（少了括号）是**赋值笔误**：不报错、该分支静默失效、看起来像「点了没反应」。写完 `grep -n 'wait_for_timeout=' 脚本` 确认没有裸赋值。
- 控件 dump 只覆盖 `button/a` 会漏掉 div 菜单项；坐标要换算时用 PIL 裁局部图放大 3 倍再问 vision（`原x=截图x/3+偏移`），比整图目测准得多。

## 教程/文章写作规范（BOSS 对「水分大」的纠偏，写教程类交付物必守）
- 教程必须从「干净环境怎么搞到」写起，关键工具（境外节点 / 浏览器通道）占独立步骤含获取方法，不许一笔带过「需要美国 IP」。
- 每一步只写三样：点哪里、填什么、看到什么算对；关键节点配实证截图（ipinfo country=US、VNC 画面、每个页面）。
- 砍掉产品介绍、muse 用法科普、推广话术和文末引导；结尾只留「一句话流程总结 + 避坑表」。
- 认可形态：`/opt/data/cache/scratch/muse_article/Muse注册保姆级教程-干货版.md`，新教程照这个骨架写。
- **写进教程的产品机制必须自己点出来过**：绑定/兑换流程会改版，二手说法（例如「WhatsApp 绑定是 wa.me 跳转发预置消息」）会让整节写错。只配自己实测截到的页面。

## WhatsApp 绑定实测（唯一官方消息渠道）
- Messaging channels 里**只有 WhatsApp 一个渠道**，没有 Telegram/SMS/飞书。面板原文：「在其他消息应用中与你的客服聊天。可用 WhatsApp」。
- 点 WhatsApp 进的是**扫码绑定页**，不是填手机号，也没有 wa.me 跳转链接。原文：「扫描此二维码，即可把你与Muse的对话连接到 WhatsApp。Muse将无法读取你的其他任何 WhatsApp 聊天，你随时可以解绑。」
- 含义：必须有**一台已登录 WhatsApp 的手机**去扫这个码（等同 WhatsApp 网页版的设备配对）。+86 号段短信投递成功率低，真实门槛在国际号/虚拟号，不是「有号码能收短信」就行。
- **WhatsApp 网页版注册不了非出口国号码，别在这条路上试第二遍**：`web.whatsapp.com` → 「创建账户」把国家代码锁成出口 IP 的国家（美国节点固定 `+1`），输入 `+86 【手机号】` 会被格式化器截成 `+1 1571211204`；用原生 `value` setter 直写同样被覆盖回 `+1`。页面上**没有国家选择器**——国旗是纯装饰 `div`（无 `role`/`tabindex`），逐点点击不弹列表，`document.querySelectorAll('select').length` 为 0。所以 +86 只能在**手机 App** 里注册（App 内国家可自由选），注册完手机就是主设备、可直接扫 Muse 的码。判据三件套：`input.value` + 国旗 `img[alt]` + `select` 数量。
- 顺序纪律：**先让 BOSS 在手机上把 WhatsApp 注册好，再谈飞书桥**。不要为了绕开手机去折腾模拟器/虚拟摄像头——那条路要管理员权限和 Hyper-V，成本远高于「手机装个 App 两分钟」。
- 绑好后 Muse 的对话出现在该 WhatsApp 账号里；飞书桥只能做同一账号的**另一个 linked device**（whatsmeow 类）去读那条会话再转发——所以 WhatsApp 号是整条链路的地基，先把它跑通再谈桥。
- 二维码是**绑定凭证**：写教程/发截图前必须模糊打码（PIL GaussianBlur 覆盖 + vision 复检确认扫不出来），并注明「动态生成会过期」。
- 登录风控口径（回答「会不会封号」用）：**同国家换 IP 登录只触发一次邮箱验证码，不封号**；真正封号的是多账号池刷 token、脚本高频打接口、邀请码刷量作弊。要守的规矩是固定同一地区节点，别跨国来回跳。

## 渠道集成研究
飞书/WhatsApp 接入 Muse 的方案对比、封号风险排序与绑定机制实测结论，见 `references/messaging-integration-options.md`。

## 现成资产
- 工作脚本：`/opt/data/cache/scratch/muse_run29.py`（一条龙：等码登录→开设置→点 Redeem→六格键盘输入→Confirm→读祝贺页→核对 Usage）；`muse_run33.py`（查本人码/名额/邀请链接，调 hatch/invite 接口）。
- Hyperbrowser API key：`/opt/data/cache/scratch/hb_key.txt`（600）；持久 profileId：`muse_profile.txt`。
- 触发新码 = 重跑 run29；BOSS 从 superxzy2013@gmail.com 读最新 6 位码，写入 `muse_code2013.txt`（脚本在等）。
- 脱敏配图库：`/opt/data/cache/scratch/muse_article/images/`（注册页/验证码/兑换入口/六格/成功页 + hb-01~hb-07 Hyperbrowser 全套：首页/注册页/美国IP实证/VNC画面/云浏览器里的Muse首屏，已裁昵称、邮箱打码）；三版稿件在同一目录：`Muse注册领10亿token-复盘素材给小七.md`（素材+事实核对表）、`小卡成稿-Muse领10亿token教程.md`（推广版）、`Muse注册保姆级教程-干货版.md`（纯操作干货版，BOSS 认可的形态）；图文打包交付用 `tar czf`（本机无 zip 命令）。
- 教程稿的「美国环境」一节直接引用 hb-05（ipinfo country=US）和 hb-07（VNC 画面）两张图，是读者最需要的实证。发布前素材核对清单在复盘素材文件末尾的事实核对表。
- 教程截图发布前：裁掉右栏含昵称的活动面板、给登录页里出现的完整邮箱打码（PIL 白块覆盖后 vision_analyze 复检确认读不出），不脱敏不能公开发。
