#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 知识星球入库 v3 —— 原生 WebSocket 直连 CDP
背景：playwright connect_over_cdp 在这台 Windows Chrome 上 180s 超时（ws 握手挂住）。
方案：自己实现最小 CDP 客户端（websocket-client），复用已有的 zsxq 页面 target。
"""
import os, re, sys, json, time, random, shutil, datetime, base64, socket, struct, hashlib
import urllib.request
import urllib.parse

CDP_HOST, CDP_PORT = "192.168.199.70", 9222
VAULT = "/opt/nas/volume2/2-AI/obsidian_vault"
SCRATCH = "/opt/data/cache/scratch"
ZSXQ_DIR = os.path.join(VAULT, "12-知识星球")
PLANETS = [("Workbuddy一人公司营", "88884585518442"), ("AI创收私研社", "88882458154112")]
THROTTLE = {"1007", "1059", "1004", "1008", "19301"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------- 最小 WebSocket 客户端 ----------
class WS:
    def __init__(self, host, port, path, timeout=30):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            c = self.s.recv(4096)
            if not c:
                raise RuntimeError("WebSocket 握手失败：连接被关闭")
            buf += c
        if b"101" not in buf.split(b"\r\n")[0]:
            raise RuntimeError(f"WebSocket 握手失败: {buf.split(chr(13).encode())[0][:120]}")
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _recv(self, n):
        while len(self.buf) < n:
            c = self.s.recv(65536)
            if not c:
                raise RuntimeError("连接关闭")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode()
        hdr = bytearray([0x81])
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 1 << 16:
            hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        hdr += mask
        hdr += bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.s.sendall(bytes(hdr))

    def recv(self):
        b0, b1 = self._recv(2)
        ln = b1 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._recv(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._recv(8))[0]
        return self._recv(ln).decode("utf-8", "replace")

    def call(self, method, params=None, timeout=40, sid=None):
        self._id += 1
        mid = self._id
        msg = {"id": mid, "method": method, "params": params or {}}
        if sid:
            msg["sessionId"] = sid
        self.send(json.dumps(msg))
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = json.loads(self.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(f"{method} 超时 {timeout}s")

    def close(self):
        try: self.s.close()
        except Exception: pass


def http_json(path):
    url = f"http://{CDP_HOST}:{CDP_PORT}{path}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode())


# ---------- 主流程 ----------
def find_zsxq_target():
    """复用一个已打开的 wx.zsxq.com 页面 target"""
    for t in http_json("/json/list"):
        if t.get("type") == "page" and "zsxq" in t.get("url", ""):
            return t
    return None


def new_target(url):
    """用 /json/new 开一个全新 target（不复用，避免导航时被 Chrome 断开）"""
    req = urllib.request.Request(
        f"http://{CDP_HOST}:{CDP_PORT}/json/new?{urllib.parse.quote(url, safe='')}",
        method="PUT")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def close_target(tid):
    try:
        urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json/close/{tid}", timeout=10)
    except Exception:
        pass


def keepalive_wait(ws, sid, total=14, step=3.5):
    """等页面加载，同时保活连接。
    根因：BOSS 那个 proxy9222.py 里 create_connection(..., timeout=10) 会把
    10 秒内无数据的连接判死（relay 的 recv 抛 timeout → finally 关掉双方）。
    所以不能 sleep 超过 ~8 秒，必须每隔几秒发一条 CDP 消息保活。
    """
    t0 = time.time()
    ready = False
    while time.time() - t0 < total:
        time.sleep(step)
        try:
            r = ws.call("Runtime.evaluate",
                        {"expression": "document.readyState + '|' + location.href",
                         "returnByValue": True}, timeout=15, sid=sid)
            v = r.get("result", {}).get("value", "")
            if "complete" in v and "zsxq.com" in v:
                log(f"    页面就绪 ({time.time()-t0:.1f}s): {v[:60]}")
                ready = True
                # 再等一会让 XHR 权限就位
                time.sleep(2)
                try:
                    ws.call("Runtime.evaluate", {"expression": "1", "returnByValue": True},
                            timeout=10, sid=sid)
                except Exception:
                    pass
                return True
        except Exception as e:
            log(f"    保活探测失败（可能被代理掐断）: {str(e)[:80]}")
            return False
    log(f"    等待超时（{total}s）")
    return ready


def fetch_topics(ws, sid, gid, count=20):
    rid = "".join(random.choices("abcdef0123456789", k=16))
    expr = f"""(async () => {{
      const r = await fetch("https://api.zsxq.com/v2/groups/{gid}/topics?scope=all&count={count}", {{
        method: 'GET', credentials: 'include',
        headers: {{'x-version':'2.56.0','x-request-id':'{rid}','x-timestamp':'{int(time.time()*1000)}',
                   'Referer':'https://wx.zsxq.com/','Accept':'application/json, text/plain, */*'}}
      }});
      return await r.text();
    }})()"""
    r = ws.call("Runtime.evaluate", {
        "expression": expr, "awaitPromise": True, "returnByValue": True},
        timeout=60, sid=sid)
    val = r.get("result", {}).get("value")
    if val is None:
        raise RuntimeError(f"页面 fetch 无返回: {json.dumps(r)[:200]}")
    try:
        d = json.loads(val)
    except Exception:
        return {"error": f"JSON 解析失败: {val[:200]}"}
    code = str(d.get("code", ""))
    if code in THROTTLE:
        return {"throttled": code}
    if not d.get("succeeded"):
        return {"error": f"code={code} {d.get('info','')}"[:200]}
    return {"topics": d.get("resp_data", {}).get("topics", [])}


def existing_ids(planet):
    root = os.path.join(ZSXQ_DIR, planet)
    ids, n = set(), 0
    if not os.path.isdir(root):
        return ids, 0
    for dp, _, fn in os.walk(root):
        for f in fn:
            if f.endswith(".md"):
                n += 1
                m = re.match(r"(\d{15,20})", f)
                if m:
                    ids.add(m.group(1))
    return ids, n


def safe(s, maxlen=60):
    return re.sub(r"\s+", " ", re.sub(r'[/\\:*?"<>|\r\n\t]', "", s)).strip()[:maxlen] or "untitled"


def build_note(planet, gid, tp, url):
    t = tp.get("topic", tp)
    tid = str(t.get("topic_id", ""))
    talk = t.get("talk") or {}
    # 作者在 talk.owner；topic.owner 为 null（踩过的坑）
    author = ((talk.get("owner") or {}).get("name")
              or (t.get("owner") or {}).get("name") or "未知")
    raw = talk.get("text") or t.get("text") or ""
    # zsxq 正文里混排 <e type="text_bold" title="%E9%9B%B6token..."> 这类标签
    # 提取 title 里的原文（已 URL-encode），并去掉剩余标签
    def _unescape(m):
        from urllib.parse import unquote
        return unquote(m.group(1))
    raw = re.sub(r'title="([^"]+)"', _unescape, raw)
    text = re.sub(r"<[^>]+>", "", raw).strip()
    create = t.get("create_time", "")
    first = text.split("\n")[0].strip() or author
    likes = t.get("likes_count", 0)
    cmts = t.get("comments_count", 0)
    fm = ["---", f'title: "{safe(first)}"', f'zsxq_group_id: "{gid}"',
          f'zsxq_group_name: "{planet}"', f'topic_id: "{tid}"', f'author: "{safe(author,30)}"',
          f'topic_type: "{t.get("type","")}"', f'created: "{create}"',
          f"likes: {likes}", f"comments_count: {cmts}",
          f"date: {datetime.date.today().isoformat()}", "source: zsxq",
          f"source_url: {url}", "tags: [知识星球, 提炼]", "added_by: 小卡", "---", "",
          f"# {safe(first)}", "",
          f"> ⭐ {planet} · {safe(author,20)} · {t.get('type','')} · {create[:10]} · 👍{likes} 💬{cmts}",
          "", "## 📝 原文", "",
          text or "（无正文：可能为纯图片/视频/附件帖）"]
    return f"{tid} - {safe(first)}.md", "\n".join(fm), tid, bool(text.strip())


def main():
    limit = 20
    for a in sys.argv[1:]:
        if a.isdigit():
            limit = int(a)

    # 用 browser 级 WebSocket（page 级会被那个反向代理掐断），再 attach 出平面会话
    ver = http_json("/json/version")
    bpath = ver["webSocketDebuggerUrl"].split(f"{CDP_PORT}", 1)[1]
    log(f"✅ browser WS: {bpath[:46]}")
    ws = WS(CDP_HOST, CDP_PORT, bpath, timeout=60)
    log("  ✅ 握手成功")

    results = []
    for planet, gid in PLANETS:
        log(f"\n=== {planet} (group/{gid}) ===")
        ids, n0 = existing_ids(planet)
        log(f"  已有 {n0} 篇，ID {len(ids)} 个")
        url = f"https://wx.zsxq.com/group/{gid}"
        sid = None
        tid = None
        try:
            # 开新 target（受 BOSS 规则约束：用完即关，站点内不超过 2 个）
            tgt = new_target(url)
            tid = tgt["id"]
            att = ws.call("Target.attachToTarget", {"targetId": tid, "flatten": True}, timeout=40)
            sid = att.get("sessionId")
            log(f"  标签已开｜会话 {str(sid)[:12]}")
            if not keepalive_wait(ws, sid, total=22, step=3.5):
                log("  ⚠️ 页面没就绪/连接被掐，继续尝试 fetch")
            r = fetch_topics(ws, sid, gid, limit)
        except Exception as e:
            log(f"  ❌ {str(e)[:200]}")
            results.append((planet, "error", str(e)[:100]))
            if sid and tid:
                try:
                    ws.call("Target.closeTarget", {"targetId": tid}, timeout=15)
                except Exception:
                    pass
            if tid:
                close_target(tid)
            time.sleep(5)
            continue

        if r.get("throttled"):
            log(f"  ⚠️ 限流 {r['throttled']} → 跳过（不硬刷）")
            results.append((planet, "throttled", r["throttled"]))
        elif r.get("error"):
            log(f"  ❌ {r['error']}")
            results.append((planet, "error", r["error"]))
        else:
            topics = r["topics"]
            log(f"  API 返回 {len(topics)} 条")
            outdir = os.path.join(ZSXQ_DIR, planet, datetime.date.today().strftime("%Y-%m"))
            os.makedirs(outdir, exist_ok=True)
            added = skipped = empty = 0
            for tp in topics:
                fname, content, topic_id, has_text = build_note(planet, gid, tp, url)
                if not topic_id or topic_id == "None":
                    empty += 1; continue
                if topic_id in ids:
                    skipped += 1; continue
                if not has_text:
                    empty += 1; continue
                tmp = os.path.join(SCRATCH, fname)
                open(tmp, "w", encoding="utf-8").write(content)
                shutil.copy(tmp, os.path.join(outdir, fname))
                ids.add(topic_id); added += 1; time.sleep(0.25)
            log(f"  ✅ 新增 {added} · 跳过(已存在) {skipped} · 空帖 {empty} → {outdir}")
            results.append((planet, "ok", added))

        # 关标签，保持 BOSS 浏览器干净
        if tid:
            try:
                ws.call("Target.closeTarget", {"targetId": tid}, timeout=15)
            except Exception:
                pass
            close_target(tid)
            log("  已关闭该标签")
        # 星球间隔退避：靠发 CDP 消息保活（那个反向代理 10 秒无数据就掐连接）
        n = 0
        while n < 10:            # 约 10 秒
            time.sleep(2)
            try:
                ws.call("Target.getTargets", {}, timeout=12)
            except Exception as e:
                log(f"  ⚠️ 保活失败，重连 browser WS: {str(e)[:60]}")
                try:
                    ver = http_json("/json/version")
                    bp = ver["webSocketDebuggerUrl"].split(f"{CDP_PORT}", 1)[1]
                    ws = WS(CDP_HOST, CDP_PORT, bp, timeout=60)
                    log("  ✅ 已重连")
                except Exception as e2:
                    log(f"  ❌ 重连失败: {str(e2)[:80]}")
                    break
            n += 1

    ws.close()
    log("\n" + "=" * 55)
    for planet, st, val in results:
        log(f"  {'✅' if st=='ok' else '⚠️' if st=='throttled' else '❌'} {planet} — "
            f"{'新增 '+str(val)+' 篇' if st=='ok' else val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
