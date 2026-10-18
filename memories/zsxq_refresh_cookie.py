#!/usr/bin/env python3
# 从 BOSS Windows(super, 已登录星球) 的 Chrome 9223 抽新鲜 zsxq cookie，
# 注入 NAS 宿主机 headless Chrome(192.168.199.2:9222)，并在 NAS 侧验证。
# 9223 在 Windows 只绑 127.0.0.1，故先确保本地 SSH 转发 127.0.0.1:9223 存在。
import json, sys, os, time, subprocess, importlib.util, urllib.request
sys.path.insert(0,"/opt/data/memories")
spec=importlib.util.spec_from_file_location("zs","/opt/data/memories/zsxq_ingest3.py")
zs=importlib.util.module_from_spec(spec); spec.loader.exec_module(zs)

KEY="/opt/data/.ssh/id_ed25519"
SSHOPTS=["-i",KEY,"-o","StrictHostKeyChecking=no","-o","UserKnownHostsFile=/dev/null",
         "-o","BatchMode=yes","-o","ConnectTimeout=6","-o","PreferredAuthentications=publickey"]

def cdp_up(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version",timeout=4).read()
        return True
    except Exception:
        return False

def ensure_tunnel():
    if cdp_up(9223): return
    host=None
    for h in ("192.168.199.184","192.168.199.70"):
        if subprocess.run(["ssh",*SSHOPTS,f"xiaoka@{h}","exit","0"]).returncode==0:
            host=h; break
    if not host:
        raise SystemExit("❌ 连不上 Windows(.184/.70)，无法刷新 cookie")
    p=subprocess.Popen(["ssh",*SSHOPTS,"-o","ExitOnForwardFailure=yes","-o","ServerAliveInterval=30",
                        "-N","-L","9223:127.0.0.1:9223",f"xiaoka@{host}"],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(8):
        time.sleep(1)
        if cdp_up(9223): return
    raise SystemExit("❌ SSH 隧道已建但 Windows 9223 无响应（Chrome 调试口没开？）")

def browser_ws(host,port):
    zs.CDP_HOST=host; zs.CDP_PORT=port
    ver=zs.http_json("/json/version")
    bp=ver["webSocketDebuggerUrl"].split(str(port),1)[1]
    return zs.WS(host,port,bp,timeout=60)

def find_zsxq_page(ws):
    ts=ws.call("Target.getTargets",{},timeout=20).get("targetInfos",[])
    for t in ts:
        if t.get("type")=="page" and "zsxq.com" in (t.get("url") or ""):
            return t["targetId"], t["url"]
    return None,None

ensure_tunnel()
# ---------- 1. Windows 侧抽 cookie ----------
wsw=browser_ws("127.0.0.1",9223)
tid,url=find_zsxq_page(wsw)
print("Windows zsxq tab:",tid,url,file=sys.stderr)
assert tid, "Windows 上没有打开的 zsxq 标签页"
att=wsw.call("Target.attachToTarget",{"targetId":tid,"flatten":True},timeout=30); sid=att["sessionId"]
time.sleep(1)
ck=wsw.call("Network.getCookies",{"urls":[
    "https://wx.zsxq.com/","https://api.zsxq.com/","https://.zsxq.com/"]},timeout=20,sid=sid)
cookies=ck.get("cookies",[])
print("抽到 cookie:",[c["name"] for c in cookies],file=sys.stderr)
wsw.close()
assert any(c["name"]=="zsxq_access_token" for c in cookies), "没抽到 zsxq_access_token"

out="/opt/data/memories/cookies/zsxq.json"
keep=[{"name":c["name"],"value":c["value"],"domain":c["domain"],"path":c.get("path","/"),
       "secure":c.get("secure",True),"httpOnly":c.get("httpOnly",False),
       "expires":c.get("expires")} for c in cookies]
json.dump(keep,open(out,"w"),ensure_ascii=False,indent=1); os.chmod(out,0o600)
tok=[c for c in cookies if c["name"]=="zsxq_access_token"][0]
print("token expires:",time.strftime("%Y-%m-%d %H:%M",time.localtime(tok.get("expires",0))),file=sys.stderr)

# ---------- 2. 注入 NAS 9222 并验证 ----------
wsn=browser_ws("192.168.199.2",9222)
tgt=zs.new_target("https://wx.zsxq.com/"); ntid=tgt["id"]
a2=wsn.call("Target.attachToTarget",{"targetId":ntid,"flatten":True},timeout=40); nsid=a2["sessionId"]
time.sleep(3)
for c in keep:
    cc={k:v for k,v in {"name":c["name"],"value":c["value"],"domain":c["domain"],
        "path":c.get("path","/"),"secure":bool(c.get("secure",True)),
        "httpOnly":bool(c.get("httpOnly",False)),"expires":c.get("expires")}.items() if v is not None}
    r=wsn.call("Network.setCookie",cc,timeout=20,sid=nsid)
    print(" 注入",cc["name"],r.get("success"),r.get("errorMessage",""),file=sys.stderr)
wsn.call("Page.enable",{},timeout=15,sid=nsid)
wsn.call("Page.navigate",{"url":"https://wx.zsxq.com/group/88884585518442"},timeout=30,sid=nsid)
time.sleep(6)
loc=wsn.call("Runtime.evaluate",{"expression":"location.href","returnByValue":True},timeout=20,sid=nsid)["result"]["value"]
print("NAS 导航后 URL:",loc,file=sys.stderr)
r=zs.fetch_topics(wsn,nsid,"88884585518442",5)
ok=bool(r.get("topics"))
print("✅ NAS 侧 API 成功，返回",len(r.get("topics",[])),"条") if ok else print("❌ NAS 侧失败:",r.get("error"),file=sys.stderr)
wsn.call("Target.closeTarget",{"targetId":ntid},timeout=15); zs.close_target(ntid); wsn.close()
sys.exit(0 if ok else 1)
