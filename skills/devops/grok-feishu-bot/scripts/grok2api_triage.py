#!/usr/bin/env python3
"""grok2api 三层诊断：healthz 状态 / cookie 有效性 / 代理稳定性。

用途：上层报 "grok error (upstream): connect failed: ConnectionResetError" 时，
一次跑完就能区分是「cookie 失效」「免费额度耗尽」还是「进程状态坏了」。

判读：
  healthz available=0 且 cookie 探针 200  → 进程状态坏了，重启 grok2api
  cookie 探针 401/403                      → cookie 失效，重新取登录态
  cookie 200 但发消息报 limit              → 真额度耗尽，等下一时间窗
  代理探针大面积失败                       → 代理/出口问题，不是账号问题

用法：python3 grok2api_triage.py
"""
import http.cookiejar
import json
import time
import urllib.request

BASE = "http://127.0.0.1:45080"
ACC = "/opt/data/services/grok2api/accounts.txt"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
PROBES = ["http://192.168.199.2:7894", "http://192.168.199.2:7891", None]
COOKIE_URL = "https://grok.com/rest/app-chat/conversations?pageSize=1"


def load_jar():
    """accounts.txt 混有注释/空行，MozillaCookieJar.load() 会抛 ValueError，只能逐行手工解析。"""
    jar = http.cookiejar.CookieJar()
    for line in open(ACC):
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 7 or not parts[0].startswith("."):
            continue
        dom, dom_spec, path, secure, exp, name, val = parts
        jar.set_cookie(http.cookiejar.Cookie(
            0, name, val, None, False, dom, dom_spec == "TRUE", dom.startswith("."),
            path, True, secure == "TRUE",
            int(exp) if exp.isdigit() else None, False, None, None, {}))
    return jar


def healthz():
    try:
        with urllib.request.urlopen(BASE + "/healthz", timeout=15) as r:
            return json.load(r)
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, str(e)[:80])}


def probe(proxy, jar, times=6):
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    op = urllib.request.build_opener(handler, urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
    ok, errs, status = 0, {}, None
    for _ in range(times):
        try:
            r = op.open(urllib.request.Request(COOKIE_URL), timeout=25)
            status = r.status
            if r.status == 200:
                ok += 1
        except urllib.error.HTTPError as e:
            status = e.code
            k = "HTTP %d" % e.code
            errs[k] = errs.get(k, 0) + 1
        except Exception as e:
            k = type(e).__name__ + ": " + str(e)[:40]
            errs[k] = errs.get(k, 0) + 1
        time.sleep(0.5)
    return ok, times, status, errs


def main():
    h = healthz()
    avail = h.get("available")
    print("[1] healthz: ok=%s accounts=%s available=%s statsig_ready=%s" % (
        h.get("ok"), h.get("accounts"), avail, h.get("statsig_ready")))
    if "error" in h:
        print("    进程可能没起：%s" % h["error"])

    jar = load_jar()
    print("[2] cookie: 键=%s sso_len=%d" % (list(c.name for c in jar), len(
        next((c.value for c in jar if c.name == "sso"), ""))))

    verdict = []
    for proxy in PROBES:
        ok, n, status, errs = probe(proxy, jar)
        print("    %-28s 成功 %d/%d  status=%s %s" % (
            proxy or "直连", ok, n, status, errs or ""))
        if proxy and ok >= n - 1 and status == 200:
            verdict.append(proxy)

    print("[3] 判读:")
    if avail == 0 and verdict:
        print("    → cookie 与网络都正常，是 grok2api 进程状态坏了：重启 run.sh")
    elif avail == 0 and not verdict:
        print("    → 网络/cookie 都不通，先修代理或重新取 cookie，别急着重启")
    elif avail and avail > 0:
        print("    → 服务可用（available=%s）。若上层仍报错，看是不是单次额度撞顶" % avail)
    else:
        print("    → healthz 无响应，检查 45080 进程")


if __name__ == "__main__":
    main()
