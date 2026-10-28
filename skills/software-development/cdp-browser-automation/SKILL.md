---
name: cdp-browser-automation
description: Drive a real logged-in Chrome over CDP for web tasks.
version: 1.0.0
author: 小卡 (Hermes)
license: MIT
metadata:
  hermes:
    tags: [cdp, playwright, browser, automation, cookies]
    related_skills: [obsidian]
---

# CDP 浏览器自动化（复用真人登录态）

## When to Use
需要登录才能做的网页活（订票、点餐、采集、后台操作）时，先读本 skill。
**核心前提**：不要在本机另开浏览器，用 `connect_over_cdp` 接 BOSS 已经登录好的 Chrome。

## 为什么必须走 CDP
本机自起浏览器（哪怕无头）暴露两个问题：出口 IP 常被风控（抖音会返空白「验证码中间页」），以及没有登录态。复用 BOSS 的 Chrome 同时解决两者——真实 IP + 真实 cookie。

## 标准接入
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("<CDP_URL>")
    ctx = b.contexts[0]          # ← 不是 b.contexts[0] or None，见下
    pg  = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(7)                # SPA 首屏必等，networkidle 对国内站常超时
    pg.set_viewport_size({"width": 1440, "height": 1100})  # 不设视口，懒加载区块不渲染
    print(pg.inner_text("body"))
    pg.close(); b.close()
```
先探活：`curl -s http://<CDP_URL>/json/version` 应返回 `webSocketDebuggerUrl`；
`/json/list` 能看到所有已开标签页和它们的登录域名——**这是最快的登录态盘点方式**。

## 读登录态：看 cookie，不看页面
```python
allc = ctx.cookies()
sites = {}
for c in allc:
    d = c["domain"]
    key = next((k for k in ("douyin","bilibili","zsxq","12306","meituan") if k in d), "other")
    sites.setdefault(key, []).append(c["name"])
```
判定表（缺失即未登录，别看页面文案猜）：

| 站点 | 关键 cookie |
|---|---|
| 抖音 | `sessionid` / `sessionid_ss` / `sid_tt` |
| B站 | `SESSDATA` / `DedeUserID` / `bili_jct` |
| 知识星球 | `zsxq_access_token` |
| 12306 | `JSESSIONID` / `BIGipServerotn` |
| 美团 | `userId` + `token`（**无** `mt_userId` = 只有游客态） |

**登录 cookie 存在 ≠ 该站功能可用**：美团有 `userId`/`token` 但没 `mt_userId`，实测照样跳登录墙。**端到端验一次真实动作**（下单页查票、点餐页读商家）才算数。

## 落盘 cookie 供离线工具用
存两份：playwright `.json`（复现登录态）+ Netscape `.txt`（喂 yt-dlp/requests）。
```python
lines = ["# Netscape HTTP Cookie File", ""]
for c in sel:
    dom = c["domain"]; flag = "TRUE" if dom.startswith(".") else "FALSE"
    lines.append(f"{dom}\t{flag}\t{c.get('path','/')}\t"
                 f"{'TRUE' if c.get('secure') else 'FALSE'}\t"
                 f"{int(c.get('expires',0) or 0)}\t{c['name']}\t{c['value']}")
```
**cookie 是登录凭据**：落盘目录不要进 Obsidian 共享库或 git，只放本地 `/opt/data` 下的专用目录。

## 通用坑
- **`connect_over_cdp` 后 `Browser` 没有 `.pages`**：`AttributeError: 'Browser' object has no attribute 'pages'`。用 `b.contexts[0].pages`，取全部 page 则是 `sum(len(c.pages) for c in b.contexts)`。
- **封装层 `js()` 会返回 `{}`**：表达式有返回值时也吐空 dict。读页面文本改用直连 playwright 的 `pg.inner_text("body")`，它稳定。
- **定位元素别靠 class 名猜**：实测美团地址栏 class 是 `addr_W3eGpu`（带 hash 后缀，会随发版变）。用「顶部区域 + 文本/类名正则」联合筛选：
  ```python
  document.querySelectorAll('div,span,a').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.top > 200 || r.width < 15) return;   // 只看顶部
    if (/addr|location|定位|地址/.test(e.className||'')) out.push(e);
  })
  ```
- **中文站 SPA 要 `time.sleep` + 放视口**，`networkidle` 基本等不到。
- **`browser_vault_*` 只对 Hermes 自管浏览器生效**；CDP 接的 Chrome 不走 vault，登录由 BOSS 自己在 Windows 上做。
- **裸 CDP 封装里 `new_tab()` 返回的是 session id 字符串，不是标签对象**（`AttributeError: 'str' object has no attribute 'eval'`）。
  `eval_js` / `call` / `goto` 都在 client 对象上：
  ```python
  with cdp.CDP(cdp.CDP_URL) as c:
      sid = c.new_tab(url, background=True)   # 只是 id
      c.eval_js("location.href")              # 在 client 上调，不传 sid
  ```
  开标签必须建时就传 `background=True`，事后 `bringToFront` 补救会抢 BOSS 焦点。
- **抓二维码/画布类元素别截整页**：先取 bounding box，再用 `Page.captureScreenshot` 的 `clip` + `scale` 裁切，
  否则二维码在 1280×900 全屏里只有指甲盖大，扫不出来。
  ```python
  c.call("Emulation.setDeviceMetricsOverride",
         {"width": 1280, "height": 900, "deviceScaleFactor": 2, "mobile": False})
  box = c.eval_js("(()=>{const r=[...document.querySelectorAll('canvas')]"
                  ".map(e=>e.getBoundingClientRect()).filter(r=>r.width>120)"
                  ".sort((a,b)=>b.width-a.width)[0];return r&&{x:r.x,y:r.y,w:r.width,h:r.height}})()")
  c.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
         "clip": {"x": box["x"]-12, "y": box["y"]-12,
                  "width": box["w"]+24, "height": box["h"]+24, "scale": 3}})
  ```

## 新开隔离上下文（注册新账号 / 不污染登录态）

要在一个**已登录**的 Chrome 里做「未登录」的事（注册小号、验证另一个账号、看游客态），不要动 `b.contexts[0]`，用 `b.new_context()` 开无痕上下文：不激活标签、不抢 BOSS 焦点、不碰他现有 cookie。

```python
ctx = b.new_context(proxy={"server": "http://<NAS_IP>:7894"},
                    locale="en-US", timezone_id="America/New_York")
```

三条必设，缺一条就卡住：

- 🔴 **新 context 不继承浏览器代理。** CDP 连的浏览器跑在 BOSS 机器上，`new_context()` 出来的是直连；大陆环境 `goto` 会一直停在 `about:blank` 直到超时（`Page.goto: Timeout`），看着像网站挂了。必须显式传 `proxy`。
- 🔴 **`locale` 决定站点文案语言。** BOSS 的 Chrome 是中文，同一个注册页会渲染成「使用邮箱注册」，`get_by_text("Sign up with email")` 直接 8s 超时。要么 `locale="en-US"` 强制英文，要么选择器同时兜底中英文案。
- 🔴 **Cloudflare 挡 headless 的 POST，`cf_clearance` 救不了。** 无头 Chrome 提交表单时后端返 `403 Attention Required`（HTML 挑战页），前端当 JSON 解析，页面显示 `Unexpected token '<', "<!DOCTYPE "... is not valid JSON`——这句就是「被 CF 挡了」的指纹，不是接口报错。实测带齐 `cf_clearance`/`__cf_bm`、换两个代理出口都一样，是浏览器指纹层。**解法只有换真实浏览器**（BOSS 的 Windows Chrome 9223）。判据：GET 能过、POST 过不去，就往这上面想。

**Windows 9223 隧道**：它只绑 `127.0.0.1`，复用 `/opt/data/memories/zsxq_refresh_cookie.py` 里的 `ensure_tunnel()`（已处理主机探测与隧道复用），先 `curl 127.0.0.1:9223/json/version` 探活再连。注意 `importlib` 加载该模块会执行它的顶层流程（会顺带跑一遍星球抓取），只想借函数就复制出来，别直接 exec_module。

**验证码类流程必须常驻等码。** 注册要邮箱验证码，收件箱在 BOSS 手里。脚本不能「提交完就退出」——context 一断就得重发码、旧码作废。正确形状：提交 → 写日志 → 轮询 `<scratch>/xxx_code.txt`（15 分钟窗口）→ 拿到码继续 → 抓 cookie；用 `background=true, persist_on_release` 挂着，并告诉 BOSS 码发到哪个邮箱、等多久。

## 权限与红线
- 支付/下单前必须 BOSS 明确确认，CDP 也不例外。
- BOSS 关机 → CDP 断，浏览器能力整体不可用（架构约束，非 bug）；汇报时先排除这个原因再排查别的。

## 站点细节
具体站点的已验证路径、URL 陷阱、geolocation 缓存问题见
`references/site-playbooks.md`。
