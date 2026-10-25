---
name: hyperbrowser-cloud-browser
description: Use when 要境外 IP 云浏览器或代注册地区受限服务。
---

# Hyperbrowser 云浏览器

用途：本机/机场 IP 被境外服务判定「不对你的国家开放」时，用 Hyperbrowser 开一台境外云浏览器跑注册流程。免费版够用（机房 IP 已是美国）。

**先做通道选择，别默认租云浏览器。** 如果用户自己电脑上已有能走境外节点的 Chrome（BOSS 的 9223 调试口），**优先驱动本机 Chrome**：cookie 存在用户配置里、登录一次长期有效、真实桌面指纹、session 不会因断连回收，也不用反复找用户要验证码。云浏览器只用于「用户本机没条件」或「不想让账号落在自己浏览器」的场景。它的代价很实：连接一断 session 立刻回收、profileId 不保存登录态、后台标签不做真实命中测试（浮层菜单点不动）。选错通道的典型后果是一晚上反复要码、还把一个验证码烧掉。

## 0. 前提：拿 API Key

若 BOSS 已在某台浏览器登录过 `app.hyperbrowser.ai`，**不要重新注册**（免费版拒收临时邮箱域名，mail.tm/guerrillamail 都失败）。直接从已登录页面挖 key：

- 页面上的 key 是遮码显示的，`Copy API Key` + `navigator.clipboard.readText()` 会报 `Document is not focused`（不能抢用户前台焦点）。
- 可行做法：扫 **localStorage/sessionStorage + React fiber 的 memoizedProps/memoizedState** 里的 `hb_[A-Za-z0-9_-]{16,}`。见 `scripts/grab_key.py`。
- 落盘 `chmod 600`，只打印长度和首尾几位，明文不进对话。

## 1. 连到 BOSS 的 Windows Chrome（9223）

BOSS 的调试口**只绑 127.0.0.1**，必须建 SSH 隧道（用户是 `xiaoka`，不是 Administrator）：

```bash
ssh -i /opt/data/.ssh/id_ed25519 -o BatchMode=yes -o StrictHostKeyChecking=no \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -N -L 9223:127.0.0.1:9223 xiaoka@192.168.199.184   # hostname=super，备用 .70
```

坑：
- `pkill -f <pattern>` 的 pattern 会匹配到承载它的 `bash -c` 命令行本身，把自己的 shell 一起 SIGTERM（隧道、脚本进程都一样）。先 `ps aux | grep` 确认 PID 再按 PID kill，或用 grep 时转义一个字符避免自匹配；kill 后用 `ps` 复核才继续。
- `timeout 30 ssh …` 会在 30 秒后断开隧道；要长驻就别加 timeout，用 `background=true`。
- 接管已有标签用 `Target.attachToTarget`，**不要** `Page.bringToFront`（BOSS 硬要求：不抢前台焦点）。

## 2. 建 session

```bash
curl -s -X POST https://api.hyperbrowser.ai/api/session \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"useProxy": false, "useStealth": true, "adblock": true, "profileId": "<可选>"}'
```

返回里有：`id` / `wsEndpoint` / **`liveUrl`（VNC 实时画面，给用户自己操作）** / `sessionUrl`。

**免费版限制（会 402）**：
- `solveCaptchas: true` → `Free plan does not support solving captchas`
- `useProxy: true` → `Free plan does not support use of proxies`

但**不开代理也是美国出口**（实测圣何塞 `169.150.221.x` / Datacamp），足以过国家级地区限制。

**session 与那条 CDP 连接同生共死**：连接一断（脚本正常退出、被 kill、未捕获异常）session 立刻不可用——`wsEndpoint` 重连必报 404 `session not found`，等几分钟也不会恢复。所以：**建 session、导航、操作、保活必须在同一个脚本、同一条连接里跑完**，不要分两次工具调用，也不要指望「先 kill 再换脚本重连」。要在连接内做多步操作，用动作文件驱动（见 muse-cloud-browser-redeem 的「单连接驱动模式」）。

## 3. profile 持久化 cookie

```bash
curl -X POST https://api.hyperbrowser.ai/api/profile -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' -d '{"name":"muse"}'
```

把返回的 `id` 作为 `profileId` 传进 session → 登录态跨 session 保留，不用每次要验证码。**首次仍要登录一次**。

## 4. 卡号/密码类输入：交回用户

不要代填任何卡号、CVV、验证码。把 `liveUrl` 发给用户，他在自己电脑打开 VNC 画面直接操作，数据不经过助手。

**发链接前先验证 liveUrl 真的能用**：`GET /api/session/<id>` 取 liveUrl，用 CDP 后台标签打开确认渲染出远程画面，再发给用户。若页面只剩一行 `failed to resolve route for session: missing redis key: session:<id>:runner`，说明该 session 没注册 runner、VNC 不可用——别让用户白点，改用 CDP 在连接内驱动，或让用户直接在自己电脑访问目标站点。liveUrl token 515 字符，聊天/日志会被打码，写成 `.txt` 附件发。

## 5. Muse 注册实测流程（2026-10）

| 步 | 页面 | 要点 |
|---|---|---|
| 1 | `muse.ai` | 中国 IP → 「不对你的国家开放」；美国 IP → 正常 |
| 2 | 首页表单 | 「Mobile number or email (required)」+ Continue，**邮箱可用** |
| 3 | 验证码页 | 「Enter your code to log in」，码发到邮箱 |
| 4 | 过了码 | 账号已创建；跳到 `/access/verification` |
| 5 | **年龄验证** | 只有三条路：信用卡（$1 预授权 5–7 天退）/ Instagram / Facebook。**没有跳过** |

年龄验证的国家下拉有 100+ 国家（含 HK/TW/SG/JP/KR/MY），**没有中国大陆** —— 国内 Visa 卡大概率被判「无法验证」，但 $1 不扣钱，可试一次。

### 验证码环节的坑（踩过）
- 填完码后 **`get_by_role("button", name="Next")` 会超时** —— 页面可能已自动提交，或 Next 不是 button。改用 `keyboard.press("Enter")` + 兜底 `locator("text=Next")`。
- **点 `Resend code` 会让旧码立刻失效**。写码文件要在 Resend **之后**清空，否则用户给的码会被自己的 `os.remove` 吃掉。
- 码约 10 分钟过期，报错文案：`That code is incorrect or has expired.`
- 每次重新提交邮箱也会触发新码 → 用户手里的码可能是上一个，务必说清「以最新邮件为准」。
- **同一邮箱短时间请求 3+ 次码，Muse 服务端会静默停发**（不是邮箱延迟/垃圾箱，是根本不发；Gmail 全局搜确认）。冷却 20 分钟/拉长到 1-2h 仍可能不恢复，最快解法是**换一个全新邮箱**（2026-10-24 实测 2012 被限频后换 2013 立刻秒到码）。
- **码页没有 Google/SSO 入口**，只有验证码 + "Use password instead"；首页也没有 Google 按钮，别再去找。

### 会话/profile 坑（重要）
- 不带 `profileId` 开的临时 session，**CDP 脚本一退出浏览器就被回收**（再用同 sid 连返回 `404 session not found`），登录态也随之丢。要跨调用保留必须：① 建持久化 profile（§3）传 `profileId`，或 ② 发码→填码→过 onboarding→到 gate→保活全在**同一个脚本、同一条 CDP 连接**里跑完。
- 一个 Hyperbrowser session **只允许一条 CDP 连接**，第二个 `connect_over_cdp` 会把第一条顶掉并导致 session 失效。
- **session 寿命由本地 CDP 进程维持**：本地脚本被 kill 或异常退出后，服务端约 1–2 分钟内回收 session（再连 404）。要把流程拆成多次工具调用，就给脚本加保活循环（周期性读 `pg.url`，不主动 `b.close()`），并保证脚本任何一步都不会未捕获异常退出。
- 注册成功后的 onboarding（`/access/disclosure`「A few things to know」）要点 **Get started → Continue** 等几步才到 `/access/verification` 信用卡 gate；别把 disclosure 误判成验证已过关就退出。
- 让 BOSS 自己填卡：脚本到 gate 后**保持连接保活**（实测 50 分钟可），同时把 `liveUrl` 给他（token 515 字符，聊天/日志会被安全打码成 `eyJhbG...`，要写成 `.txt` 附件发，或调 GET `/api/session/<id>` 重新取）。

### 自动化脚本健壮性（每条都是整条链作废级）
- **所有 `pg.screenshot()` / `inner_text()` 必须包 try/except**：设置弹窗打开时 screenshot 可能超时（卡在等字体加载），未捕获的 Playwright 异常让脚本当场退出 → session 回收 → 登录态丢 → 再烧用户一个验证码。截图是诊断手段不是必经步骤，失败了继续主流程。
- **启动前 `grep -n 'time.sleep=[^ (]' 脚本`**：`time.sleep=.5` 是合法 Python（给模块属性赋值），ast.parse 不报错，运行时把 `time.sleep` 变成 float，之后所有 sleep 全崩 `'float' object is not callable`。写完长流程脚本先跑这条 grep 再 launch。
- **选择器撞名就换像素坐标**：聊天类页面的 `aria-label="More options"` 每个消息气泡都有一个，按序遍历永远点不到左下角真正的菜单。路径：截图 → vision 问目标按钮的像素坐标 → `pg.mouse.click(x,y)` → 用「页面文本是否出现菜单项」验证点对了，而不是假设点对了。
- **每次重跑等待验证码的脚本前**：先确认旧等待进程已死 + `rm` 码文件。残留的旧进程/旧码文件会把用户报来的新码吃掉或配对到过期邮件；同时跟用户强调「只看最新一封邮件」，旧码提交会报 `incorrect or has expired` 白烧一次。

### 邀请码兑换（被邀请方）的坑
- **分清两个页面**：设置菜单里的 "Invite" 打开的多半是 **Invite friends（邀请别人）** 页——显示你自己的码 + "Scratch across the card" 刮刮卡，**没有输入框**，填不了别人的码。被邀请方真正的兑换入口在 **Settings → General → Redeem invite code**。判据：真兑换页必有可编辑的文本 input；只看到自己的码就说明点错了页，别在 Invite friends 页里瞎填。
- **不要假设 profileId=已登录**：带持久档案开新 session 仍可能落在登录页（实测发生）。脚本开头先探测页面含 "Mobile number or email"，是登录页就走「填邮箱→Continue→等验证码文件」流程，把发码和等码写进同一脚本（码文件轮询模式，见 §5 验证码坑）。
- **48h 窗口先算再动**：兑换窗口从注册落库时间起算。动手前先查注册时间戳算剩余窗口，别把「入口没找到」误判成「窗口已过」而急着重注册新号。
- **自己的码 ≠ 别人的码**：两者格式相似且首字符 O/0 易混。填码前与原始来源（截图/页面）逐字符核对，填错即兑换失败且可能消耗名额。
- 兑换页脚本要「找到输入框→填码→点 Redeem/Submit」一条龙在同一次 CDP 连接里跑完，中途截图+dump 全文落日志，方便事后核对成败。

## 5b. 给教程/文章抓配图截图（不抢 BOSS 前台）
- 抓外部网页截图一律走 BOSS Chrome 的 CDP 后台标签：`Target.createTarget(url, background=True)` → 等 6-9s → `Page.captureScreenshot`（tmo 25s+）→ `Target.closeTarget`。用 /opt/data/memories/cdp.py 的 `new_tab(background=True)` + `goto()`，别用 Playwright connect 后再 `new_page()` 抢焦点。
- 登录态不跟后台标签走：BOSS 已登录 app.hyperbrowser.ai，新开的后台标签抓控制台仍可能落在登录页。别反复重试截图，改用 API（GET /api/session 等）取数据；官网首页/注册页等无需登录的页面才能直接截。
- noVNC 截图技巧：liveUrl 画面就是云 Chrome 本体，新 session 默认停在 about:blank。要有内容的 VNC 图，先在**同一条脚本里**用 CDP 把 session 页面导航到目标网址（占住唯一的 CDP 连接），再从 BOSS Chrome 后台标签开 liveUrl 截图。
- 免费档 POST /api/session 连开 3+ 次会 429 Too Many Requests（间隔几分钟才恢复）。截图任务把「开 session→导航→抓图」写进一个脚本一次跑完，减少 session 数；DELETE /api/session 收尾可能 404（session 已被回收），404 就当已删除，别重试。

## 6. 收尾

脚本 `finally` 里 `DELETE /api/session/<id>`，免费额度按分钟计。
