#!/usr/bin/env python3
"""借用 BOSS Windows Chrome(9223, 经 SSH 隧道 19224) 的已登录 Gitea 会话，创建 xiaodou 账号。
只开后台标签，不抢前台焦点；只关自己开的标签。
用法: python3 gitea_admin_cdp.py probe
      python3 gitea_admin_cdp.py create
"""
import json, sys, time, urllib.request
from websocket import create_connection

LOCAL = "127.0.0.1:19224"
BASE = f"http://{LOCAL}"

def http(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=10).read())

class Tab:
    def __init__(self, url="about:blank"):
        t = http("/json/new?" + url) if False else None
        # 用 Target.createTarget(background=True) 建标签，避免抢焦点
        self.browser = None
        ver = http("/json/version")
        self.ws_b = ver["webSocketDebuggerUrl"].replace("127.0.0.1:9223", LOCAL)
        self.b = create_connection(self.ws_b, timeout=30, suppress_origin=True)
        self._id = 0
        self._send("Target.createTarget", {"url": url, "background": True})
        tid = self._recv_result()["targetId"]
        self.tid = tid
        self._send("Target.attachToTarget", {"targetId": tid, "flatten": True})
        self.sid = self._recv_result()["sessionId"]

    def _send(self, method, params=None, session=None):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.b.send(json.dumps(msg))
        return self._id

    def _recv_result(self, timeout=25):
        end = time.time() + timeout
        while time.time() < end:
            raw = self.b.recv()
            m = json.loads(raw)
            if "id" in m:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
        raise TimeoutError("cdp recv timeout")

    def cmd(self, method, params=None, timeout=25):
        self._send(method, params, session=self.sid)
        return self._recv_result(timeout)

    def js(self, expr):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value")

    def goto(self, url, wait=3.0):
        self.cmd("Page.navigate", {"url": url})
        time.sleep(wait)

    def close(self):
        try:
            self.cmd("Target.closeTarget", {"targetId": self.tid})
        except Exception:
            pass

def probe(t):
    t.goto("http://192.168.199.2:3000/", 4)
    txt = t.js("document.body.innerText.slice(0,400)") or ""
    user = t.js("(document.querySelector('.item[href*=\"/\"] .gt-ellipsis')||{}).innerText || (document.querySelector('a[href*=\"_profile\"]')||{}).innerText || ''")
    print("URL:", t.js("location.href"))
    print("登录态:", "已登录" if ("Dashboard" in txt or "仪表盘" in txt or "Sign In" not in txt) else "未登录")
    print("首页文本:", txt[:200].replace("\n", " | "))
    print("用户:", user)

def create(t, user="xiaodou", pw="qSukliE8uhLKCC0DvTMxUcuq", email="xiaodou@a2a.local"):
    t.goto("http://192.168.199.2:3000/admin/users/new", 3)
    url = t.js("location.href")
    print("表单页:", url)
    if "/admin/users/new" not in url:
        print("!! 未进入管理员建号页，登录态或权限不足"); return False
    # 填表
    t.js(f"""(() => {{
      const set=(n,v)=>{{const e=document.querySelector(`input[name="${{n}}"]`); if(e){{e.value=v; e.dispatchEvent(new Event('input',{{bubbles:true}}));}}}};
      set('user_name','{user}'); set('login_name','{user}'); set('email','{email}');
      set('password','{pw}'); set('retype','{pw}');
      const c=document.querySelector('input[name="must_change_password"]'); if(c) c.checked=false;
      return document.querySelectorAll('input').length;
    }})()""")
    time.sleep(0.5)
    print("已填字段数:", t.js("document.querySelectorAll('input').length"))
    t.js("""(() => {const f=document.querySelector('form'); if(f){f.querySelector('button[type=submit],button.ui.green.button').click(); return 'clicked'} return 'noform'})()""")
    time.sleep(4)
    print("提交后 URL:", t.js("location.href"))
    print("提示:", (t.js("document.body.innerText.slice(0,300)") or "").replace("\n", " | ")[:300])
    return True

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    t = Tab("about:blank")
    try:
        if mode == "probe":
            probe(t)
        else:
            probe(t)
            create(t)
    finally:
        t.close()
