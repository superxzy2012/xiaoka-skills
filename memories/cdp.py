#!/usr/bin/env python
"""
cdp.py — 远程 CDP 客户端（Windows ChromeCDP via netsh portproxy）

已实测：
  - cdp_url = http://192.168.199.184:9224
  - 握手必须 websocket-client + suppress_origin=True
  - ws URL 要把 127.0.0.1 换成 Windows 的局域网 IP
  - connect_over_cdp 后 Browser 无 .pages；Target.createTarget + attach 才稳
  - Storage.getCookies 参数不能传 browserContextId（Invalid parameters）
  - 抖音 sessionid 是 HttpOnly，document.cookie 看不到，必须走 Storage.getCookies

用法：
    from cdp import CDP
    with CDP() as c:
        print(c.eval_js("document.title"))
        print(c.cookies("douyin.com"))
"""
import json
import re
import time
import urllib.request

from websocket import create_connection

CDP_URL = "http://192.168.199.184:9224"


class CDP:
    def __init__(self, url=CDP_URL, host=None, timeout=30):
        ver = json.load(urllib.request.urlopen(url + "/json/version", timeout=10))
        ws_url = ver["webSocketDebuggerUrl"]
        if host:  # 127.0.0.1 → Windows 局域网 IP（portproxy 后的地址）
            ws_url = ws_url.replace("127.0.0.1", host)
        self.host = host or self._guess_host(url)
        self.ws = create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0
        self._sid = None
        self._tid = None

    @staticmethod
    def _guess_host(url):
        m = re.match(r"http://([\d.]+):", url)
        return m.group(1) if m else "127.0.0.1"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ---------- 底层 ----------
    def call(self, method, params=None, sid=None, tmo=30):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        if sid:
            msg["sessionId"] = sid
        self.ws.send(json.dumps(msg))
        t0 = time.time()
        while time.time() - t0 < tmo:
            raw = self.ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            r = json.loads(raw)
            if r.get("id") == self._id:
                return r
        return None

    # ---------- 标签管理 ----------
    def new_tab(self, url="about:blank"):
        """新建自己的标签，绝不碰 BOSS 现有标签。"""
        r = self.call("Target.createTarget", {"url": url})
        if not r or "result" not in r:
            raise RuntimeError("createTarget failed: " + json.dumps(r, ensure_ascii=False)[:200])
        self._tid = r["result"]["targetId"]
        r = self.call("Target.attachToTarget", {"targetId": self._tid, "flatten": True})
        self._sid = r["result"]["sessionId"]
        self.call("Page.enable", {}, self._sid)
        return self._tid

    def goto(self, url, wait=6):
        self.call("Page.navigate", {"url": url}, self._sid)
        time.sleep(wait)

    def close(self):
        try:
            if self._tid:
                self.call("Target.closeTarget", {"targetId": self._tid})
        except Exception:
            pass
        try:
            self.ws.close()
        except Exception:
            pass

    # ---------- 高层 ----------
    def eval_js(self, expr, wait=0):
        if wait:
            time.sleep(wait)
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True}, self._sid)
        if not r or "result" not in r:
            return None
        inner = r["result"].get("result", {})
        if "value" in inner:
            return inner["value"]
        if "description" in inner:
            return inner["description"]  # 未捕获异常
        return None

    def cookies(self, domain="douyin.com"):
        """含 HttpOnly。返回 {name: value}。"""
        r = self.call("Storage.getCookies", {}, self._sid)
        if not r or "result" not in r:
            return {}
        out = {}
        for c in r["result"].get("cookies", []):
            if domain in c.get("domain", ""):
                out[c["name"]] = c["value"]
        return out

    def cookie_header(self, domain="douyin.com"):
        ck = self.cookies(domain)
        return "; ".join(f"{k}={v}" for k, v in ck.items())


if __name__ == "__main__":
    with CDP() as c:
        c.new_tab()
        c.goto("https://www.douyin.com/", wait=7)
        ck = c.cookies("douyin.com")
        print(f"抖音 {len(ck)} cookie")
        print("已登录" if "sessionid" in ck else "未登录")
        b = c.cookies("bilibili.com")
        print(f"B站 {len(b)} cookie · 已登录" if "SESSDATA" in b else f"B站 {len(b)} cookie · 未登录")