#!/usr/bin/env python3
"""
nas_cdp.py — NAS 容器内 CDP 客户端 (T-012)

替代「局域网电脑 Chrome」依赖：所有抖音/B站 CDP 操作走 NAS 自建容器。

架构:
    NAS 宿主 docker 容器 cdp-chrome (zenika/alpine-chrome, Chromium 124)
      - 端口: 192.168.199.2:9222 (只绑 LAN IP, 不绑 0.0.0.0)
      - 卷:   /volume2/2-AI/cdp-profile -> /data  (登录态持久化, 重启存活)
      - 限制: --shm-size=1g --memory=1g --restart unless-stopped
    小卡容器 --HTTP--> http://192.168.199.2:9222

用法:
    /opt/data/.venv-browser/bin/python nas_cdp.py status
    /opt/data/.venv-browser/bin/python nas_cdp.py refresh-cookies   # 从 Windows Chrome 拉登录态注入
    /opt/data/.venv-browser/bin/python nas_cdp.py douyin <url>
    /opt/data/.venv-browser/bin/python nas_cdp.py bilibili <url>

关键坑:
  - 抖音页面 wait_until="domcontentloaded" 会挂死 -> 用 "commit" + wait_for_timeout
  - 抖音 sessionid 是 HttpOnly, document.cookie 取不到 -> 必须 Storage.getCookies
  - 登录态存 SQLite 加密, grep 明文查不到属正常, 以行为验证为准
  - 登录态来源: Windows Chrome CDP http://192.168.199.184:9224 (只读导出, 不碰BOSS标签)
"""
import json
import re
import sys
import time

CDP_URL = "http://192.168.199.2:9222"
SRC_CDP = "http://192.168.199.184:9224"
COOKIE_DUMP = "/opt/data/memories/cookies/douyin_nas.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


# ---------------- 底层: 只读拉取源浏览器 cookies ----------------
class RawCDP:
    """极简 CDP 客户端 (websocket-client)。suppress_origin 必须开。"""

    def __init__(self, url):
        import urllib.request

        from websocket import create_connection

        ver = json.load(urllib.request.urlopen(url + "/json/version", timeout=10))
        ws_url = ver["webSocketDebuggerUrl"]
        host = re.match(r"http://([\d.]+):", url).group(1)
        ws_url = ws_url.replace("127.0.0.1", host)
        self.ws = create_connection(ws_url, timeout=30, suppress_origin=True)
        self._id = 0

    def call(self, method, params=None, tmo=30):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        t0 = time.time()
        while time.time() - t0 < tmo:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                return msg
        raise TimeoutError(method)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def export_cookies(src=SRC_CDP, out=COOKIE_DUMP):
    """只读导出源浏览器全部 cookie。不新建/不关闭任何标签。"""
    c = RawCDP(src)
    try:
        resp = c.call("Storage.getCookies", {})  # 注意: 不能传 browserContextId
        if "error" in resp:
            raise RuntimeError(resp["error"])
        cookies = resp["result"]["cookies"]
        json.dump(cookies, open(out, "w"), ensure_ascii=False)
        return cookies
    finally:
        c.close()


def _to_playwright(cookies, domain_kw):
    out = []
    for k in cookies:
        if domain_kw not in (k.get("domain") or ""):
            continue
        if not k.get("name"):
            continue
        c = {"name": k["name"], "value": k["value"],
             "domain": k["domain"], "path": k.get("path", "/")}
        if k.get("expires", -1) and k["expires"] > 0:
            c["expires"] = float(k["expires"])
        if k.get("httpOnly"):
            c["httpOnly"] = True
        if k.get("secure"):
            c["secure"] = True
        if k.get("sameSite") in ("Strict", "Lax", "None"):
            c["sameSite"] = k["sameSite"]
        out.append(c)
    return out


def refresh(dump=COOKIE_DUMP):
    """从源浏览器导出并注入 NAS CDP 容器。"""
    from playwright.sync_api import sync_playwright

    cookies = export_cookies(out=dump)
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        n = 0
        for kw in ("douyin", "bilibili"):
            sub = _to_playwright(cookies, kw)
            if sub:
                ctx.add_cookies(sub)
                n += len(sub)
        b.close()
    return n


# ---------------- 业务: 页面操作 ----------------
def new_tab(url=None, background=True):
    """开新标签。background=True 保证不抢焦点 (BOSS 硬要求)。"""
    from playwright.sync_api import sync_playwright

    p = sync_playwright().start()
    b = p.chromium.connect_over_cdp(CDP_URL)
    ctx = b.contexts[0]
    page = ctx.new_page()
    if url:
        page.goto(url, wait_until="commit", timeout=45000)
    return p, b, page


def parse_douyin(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        try:
            page.goto(url, wait_until="commit", timeout=45000)
            page.wait_for_timeout(12000)
            info = page.evaluate("""() => {
                const r = {url: location.href, title: document.title};
                const v = document.querySelector('video');
                if (v) r.video_src = v.src || (v.querySelector('source')||{}).src || null;
                const d = document.querySelector('meta[name="description"]');
                if (d) r.desc = d.content;
                r.loading = (document.body.innerText||'').includes('视频数据加载中');
                return r;
            }""")
            m = re.search(r"/video/(\d+)", page.url)
            info["video_id"] = m.group(1) if m else None
            return info
        finally:
            page.close()
            b.close()


def parse_bilibili(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        try:
            page.goto(url, wait_until="commit", timeout=45000)
            page.wait_for_timeout(9000)
            return page.evaluate("""() => {
                const r = {url: location.href, title: document.title};
                const h1 = document.querySelector('h1');
                if (h1) r.h1 = h1.innerText.trim();
                const m = document.querySelector('meta[name="description"]');
                if (m) r.desc = m.content.slice(0, 300);
                const up = document.querySelector('.up-name, .up-info-name');
                if (up) r.up = up.innerText.trim();
                r.has_video = !!document.querySelector('video');
                return r;
            }""")
        finally:
            page.close()
            b.close()


def status():
    import urllib.request
    try:
        with urllib.request.urlopen(CDP_URL + "/json/version", timeout=6) as r:
            v = json.load(r)
        tabs = json.load(urllib.request.urlopen(CDP_URL + "/json/list", timeout=6))
        return {"up": True, "browser": v.get("Browser"), "ua": v.get("User-Agent"),
                "tabs": len(tabs)}
    except Exception as e:
        return {"up": False, "err": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif cmd == "refresh-cookies":
        print("injected:", refresh())
    elif cmd == "douyin":
        print(json.dumps(parse_douyin(sys.argv[2]), ensure_ascii=False, indent=2))
    elif cmd == "bilibili":
        print(json.dumps(parse_bilibili(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
