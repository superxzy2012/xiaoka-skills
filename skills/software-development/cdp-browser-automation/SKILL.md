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

## 权限与红线
- 支付/下单前必须 BOSS 明确确认，CDP 也不例外。
- BOSS 关机 → CDP 断，浏览器能力整体不可用（架构约束，非 bug）；汇报时先排除这个原因再排查别的。

## 站点细节
具体站点的已验证路径、URL 陷阱、geolocation 缓存问题见
`references/site-playbooks.md`。
