#!/usr/bin/env python3
"""在 AFS(Chat2API) 里把某个网页供应商的登录窗口打开，停在滑块/扫码页，等人接手。

用法：python3 afs_open_login.py [provider_text] [--cdp http://192.168.199.2:9322]
默认 provider_text = 'GLM'。依赖 /opt/data/.venv-browser/bin/python（playwright）。

能自动做到：供应商 → 添加账户 → 下一步 → OAuth 登录 tab → 打开 OAuth 登录 → 找到 chatglm 页并截图。
做不到（必须真人）：过滑块验证、扫码。屏幕在 noVNC http://192.168.199.2:6080。
"""
import sys
import time

from playwright.sync_api import sync_playwright

CDP = "http://192.168.199.2:9322"
PROVIDER = "GLM"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if args:
    PROVIDER = args[0]
for a in sys.argv[1:]:
    if a.startswith("--cdp"):
        CDP = a.split("=", 1)[1] if "=" in a else CDP


def click_text(pg, txt):
    try:
        pg.get_by_text(txt, exact=True).first.evaluate("e => e.click()")
        return True
    except Exception:
        return False


def click_coord(pg, txt):
    """React Tab / 内层 span 场景：文字命中的元素点不动，按坐标点。"""
    boxes = pg.evaluate(
        """(t) => {const o=[];document.querySelectorAll('*').forEach(e=>{
            const s=(e.innerText||'').trim(); if(s===t){const r=e.getBoundingClientRect();
            if(r.width>0) o.push({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});}});return o;}""",
        txt,
    )
    if not boxes:
        return False
    pg.mouse.click(boxes[0]["x"], boxes[0]["y"])
    return True


with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(CDP)
    ctx = b.contexts[0]
    pg = ctx.pages[0]
    if "添加账户" not in pg.evaluate("document.body.innerText"):
        click_text(pg, "供应商")
        time.sleep(2)
        click_text(pg, PROVIDER)
        time.sleep(2)
    print("添加账户:", click_text(pg, "添加账户"))
    time.sleep(3)
    print("下一步:", click_text(pg, "下一步"))
    time.sleep(2)
    print("OAuth tab:", click_coord(pg, "OAuth 登录"))
    time.sleep(2)
    print("打开 OAuth 登录:", click_text(pg, "打开 OAuth 登录"))
    for _ in range(12):
        time.sleep(2)
        if any("chatglm" in x.url or "oauth" in x.url for x in ctx.pages):
            break
    target = None
    for x in ctx.pages:
        if "chatglm" in x.url or "oauth" in x.url:
            target = x
    if target is None:
        print("NO_LOGIN_PAGE  pages=", [u.url[:60] for u in ctx.pages])
        raise SystemExit(1)
    print("LOGIN_URL:", target.url)
    print("LOGIN_TEXT:", target.evaluate("document.body.innerText")[:200].replace("\n", " | "))
    target.screenshot(path="/opt/data/cache/scratch/afs_login_window.png")
    print("SHOT: /opt/data/cache/scratch/afs_login_window.png")
    print("NEXT: 让 BOSS 在 noVNC http://192.168.199.2:6080 过滑块 + 扫码")
