#!/usr/bin/env python3
"""小豆入列看门狗：查组网 peer / Gitea 可达 / 总线 PING 回执，卡住则群里 @小豆 催一次。
状态落 /opt/data/cache/xiaodou_watch_state.json，避免刷屏。
用法: python3 xiaodou_watch.py [--nudge]   (不带 --nudge 只体检不发群)"""
import json, re, subprocess, sys, time, urllib.request, pathlib, datetime

CHAT = "oc_568730200f9a3120919be177344687e5"
XIAODOU_OPENID = "ou_4b8b06fc47ac1a6372bae51f01aebbd4"
PEER = "9595DAD2AA42636BOW"
MESH_IP = "100.66.1.9"
WATCH_REPO = pathlib.Path("/opt/data/cache/a2a-bus-watch")
STATE = pathlib.Path("/opt/data/cache/xiaodou_watch_state.json")
NUDGE_GAP = 4 * 3600      # 两次催办最小间隔
NUDGE_MAX_PER_DAY = 3

def sh(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def ssh_nas(script, timeout=90):
    return sh(f"ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "
              f"-i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 {json.dumps('sh -s')} <<'EOS'\n{script}\nEOS", timeout)

def http(url, timeout=8):
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "xiaoka-watch"})
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0

def mesh_state():
    """返回 (peer 在册?, .9:16880 码, Gitea 码)"""
    script = ("sudo -n /usr/bin/docker exec owjdxb sh -c \"grep -aE 'addRoute|RouteAdd' "
              "/data/store/OWData/owjdxb/.ownbsv/NodeBabyLinkService.log | grep -a " + PEER +
              " | tail -1 | grep -oE '100[.]66[.]1[.][0-9]+' | tail -1\"; "
              f"curl -s -m 5 -o /dev/null -w 'nblink=%{{http_code}} ' http://{MESH_IP}:16880/; "
              "curl -s -m 5 -o /dev/null -w 'gitea=%{http_code}\\n' http://100.66.1.7:3000/api/v1/version")
    rc, out = ssh_nas(script)
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    peer_line = next((l for l in lines if re.match(r"^100\.66\.1\.\d+$", l)), "")
    m = re.search(r"nblink=(\d+)\s+gitea=(\d+)", out)
    return bool(peer_line), (int(m.group(1)) if m else 0), (int(m.group(2)) if m else 0), peer_line

def bus_ping():
    """返回 (小豆近 24h 有活动?, 证据列表)"""
    if not WATCH_REPO.exists():
        sh(f"git clone -q --depth 1 http://100.66.1.7:3000/anc/a2a-bus.git {WATCH_REPO}", 240)
    else:
        sh(f"git -C {WATCH_REPO} fetch -q --depth 1 origin main && git -C {WATCH_REPO} reset -q --hard origin/main", 240)
    if not WATCH_REPO.exists():
        return None, []
    ev = []
    rc, out = sh(f"git -C {WATCH_REPO} log --since='30 hours ago' --format='%an|%s'")
    for l in out.splitlines():
        if "xiaodou" in l.lower():
            ev.append("commit: " + l[:70])
    rc, out = sh(f"cd {WATCH_REPO} && ls -t outbox/ 2>/dev/null | grep -i xiaodou | head -3")
    for f in [x for x in out.splitlines() if x.strip()]:
        ev.append("outbox: " + f)
    return bool(ev), ev[:5]

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"last_nudge": 0, "nudge_day": "", "nudge_count": 0}

def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False))

def nudge(text, to_q=False):
    target = "ou_b172b28aa8416f7fca826bc151b9cbb8" if to_q else XIAODOU_OPENID
    rc, out = sh(f'cd /opt/data/memories && python3 ping_jarvis.py {CHAT} {target} {json.dumps(text)}', 90)
    return rc == 0 and "code= 0" in out, out[-160:]

def main():
    do_nudge = "--nudge" in sys.argv
    now = time.time()
    today = datetime.date.today().isoformat()
    peer_ok, nb, gt, peer_line = mesh_state()
    ping_ok, ping_files = bus_ping()
    st = load_state()
    if st.get("nudge_day") != today:
        st["nudge_day"], st["nudge_count"] = today, 0

    print(f"[{datetime.datetime.now():%F %T}] peer_in_log={peer_ok} nblink={nb} gitea={gt} ping_receipt={ping_ok} {ping_files}")
    print(f"  peer_line: {peer_line[:80]}")

    ok = (nb == 404 or nb == 200) and gt == 200
    if ping_ok:
        print("  ✅ 链路已闭环（总线已有小豆回执）")
    elif not ok:
        print("  ⚠️ 链路有断点，需从 NAS 侧查日志")
    else:
        print("  ⏳ 组网与 Gitea 都通，等小豆 clone + PING 回执")
    if ping_ok and "commit:" in " ".join(ping_files):
        print("  ✅ 小豆近 30h 有 commit 活动（链路闭合后仍在干活）")

    if do_nudge and not ping_ok:
        cooled = now - st.get("last_nudge", 0) > NUDGE_GAP
        quota = st.get("nudge_count", 0) < NUDGE_MAX_PER_DAY
        if cooled and quota:
            msg = (f"小豆，进度卡在你这边：组网已通（peer {PEER} → {MESH_IP}），Gitea 3000 也 200。\n"
                   "请跑：curl -m5 -o /dev/null -w '%{http_code}\\n' http://100.66.1.7:3000/api/v1/version\n"
                   "通了就 clone → sync.sh → push PING 回执 → 群里发「PING xiaodou ✅」。\n"
                   "哪一步报错就把报错原文贴出来（000=组网不通 / 401=密码不对 / 403=没授权），我从 NAS 侧定位。")
            sent, detail = nudge(msg)
            print(f"  📣 nudge sent={sent} {detail}")
            if sent:
                st["last_nudge"] = now
                st["nudge_count"] = st.get("nudge_count", 0) + 1
        else:
            print(f"  (催办冷却中 last={st.get('last_nudge')} count={st.get('nudge_count')})")
        # 升级：催了一天仍无回复 → 群内 @QUEEN 喊人
        esc = st.get("escalated_at", 0)
        if (now - esc > 24 * 3600) and (now - st.get("last_nudge", 0) > NUDGE_GAP):
            esc_msg = (f"【QUEEN·升级】小豆入列已卡 >24h：组网 peer {PEER} 在线、Gitea 3000=200，"
                       "但总线无小豆近 30h 活动，群内催办无回。需 QUEEN 出面确认小豆是否还需联调。")
            sent, detail = nudge(esc_msg, to_q=True)
            print(f"  🚨 escalate sent={sent} {detail}")
            if sent:
                st["escalated_at"] = now
    save_state(st)

if __name__ == "__main__":
    main()
