#!/usr/bin/env python
"""
cdp_client.py — minimal raw-CDP client for a REMOTE Chromium.

Stdlib + `websocket-client`. Owns its own tab so the user's tabs are never touched.

Why raw CDP instead of playwright: works when `connect_over_cdp` is unavailable or its
JS-eval wrapper returns junk, and gives access to `Storage.getCookies`, which is the
only reliable way to read a login state (session cookies are HttpOnly and invisible to
`document.cookie`).

Usage:
    from cdp_client import CDP
    with CDP("http://<host>:<port>") as c:
        c.new_tab()
        c.goto("https://example.com/")
        print(c.eval_js("document.title"))
        print(sorted(c.cookies("example.com")))
        hdr = c.cookie_header("example.com")   # for curl / yt-dlp

Install:  uv pip install --python <venv>/bin/python websocket-client
"""
import json
import re
import time
import urllib.request

from websocket import create_connection

DEFAULT_URL = "http://127.0.0.1:9222"


class CDP:
    """Own-tab CDP client. The relay host is auto-detected from the URL and substituted
    for 127.0.0.1 in the webSocketDebuggerUrl, because a loopback relay reports its
    internal loopback host and that address is unreachable from the client."""

    def __init__(self, url=DEFAULT_URL, host=None, timeout=30):
        ver = json.load(urllib.request.urlopen(url.rstrip("/") + "/json/version", timeout=15))
        ws_url = ver["webSocketDebuggerUrl"]
        self.host = host or self._host_from(url)
        if self.host:
            ws_url = ws_url.replace("127.0.0.1", self.host)
        self._ws = create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0
        self._sid = None
        self._tid = None

    @staticmethod
    def _host_from(url):
        m = re.match(r"https?://([\d.]+):", url)
        return m.group(1) if m else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- wire ----
    def call(self, method, params=None, sid=None, timeout=30):
        """Send one command, consume interleaved events, return the matching reply."""
        self._id += 1
        want = self._id
        msg = {"id": want, "method": method, "params": params or {}}
        if sid:
            msg["sessionId"] = sid
        self._ws.send(json.dumps(msg))
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame = self._ws.recv()
            if isinstance(frame, bytes):
                frame = frame.decode("utf-8", "replace")
            reply = json.loads(frame)
            if reply.get("id") == want:
                return reply
        return None

    # ---- own-tab discipline ----
    def new_tab(self, url="about:blank"):
        r = self.call("Target.createTarget", {"url": url})
        if not r or "result" not in r:
            raise RuntimeError("Target.createTarget failed: %s" % json.dumps(r)[:200])
        self._tid = r["result"]["targetId"]
        r = self.call("Target.attachToTarget", {"targetId": self._tid, "flatten": True})
        self._sid = r["result"]["sessionId"]
        self.call("Page.enable", {}, self._sid)
        return self._tid

    def goto(self, url, wait=6):
        self.call("Page.navigate", {"url": url}, self._sid)
        time.sleep(wait)          # SPAs need real wall clock; networkidle rarely settles

    def close(self):
        for fn, arg in (("Target.closeTarget", {"targetId": self._tid}),):
            try:
                if arg.get("targetId"):
                    self.call(fn, arg)
            except Exception:
                pass
        try:
            self._ws.close()
        except Exception:
            pass

    # ---- reads ----
    def eval_js(self, expr, wait=0):
        """Returns the value, an exception description, or None on failure."""
        if wait:
            time.sleep(wait)
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True}, self._sid)
        if not r or "result" not in r:
            return None
        inner = r["result"].get("result", {})
        if "value" in inner:
            return inner["value"]
        return inner.get("description")

    def cookies(self, domain):
        """{name: value} INCLUDING HttpOnly. Pass {} to getCookies -- sending
        browserContextId (even as null) returns -32602 Invalid parameters."""
        r = self.call("Storage.getCookies", {}, self._sid)
        if not r or "result" not in r:
            return {}
        return {c["name"]: c["value"] for c in r["result"].get("cookies", [])
                if domain in c.get("domain", "")}

    def cookie_names(self, domain):
        return sorted(self.cookies(domain))

    def cookie_header(self, domain):
        return "; ".join("%s=%s" % kv for kv in self.cookies(domain).items())

    def logged_in(self, domain, session_keys):
        """session_keys: names whose presence indicates a real session on that site.
        Names are necessary, not sufficient -- confirm with one authed request."""
        return [k for k in session_keys if k in self.cookies(domain)]


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    with CDP(url) as c:
        c.new_tab()
        c.goto("about:blank", wait=1)
        print("bridge OK ->", url)
        print("cookie domains reachable:", bool(c.cookies("")))
