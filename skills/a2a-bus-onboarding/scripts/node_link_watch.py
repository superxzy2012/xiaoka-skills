#!/usr/bin/env python3
"""看门狗：监控某 A2A 节点是否真的活在网络里并在总线上活动。
用法: python3 node_link_watch.py <peerid> <mesh_ip> <bus_author> [--openid <oid>] [--chat <cid>] [--nudge]
  peerid     节点小宝 peerid（18位 OW 结尾）
  mesh_ip    该节点组网 IP（100.66.1.x）
  bus_author 总线 commit author 名（如 xiaodou），用于 git log 匹配
  --openid   飞书 open_id，用于 @催办（缺省只体检不催）
  --chat     群 chat_id（缺省管理群）
  --nudge    带此开关才发催办；不带只打印体检
状态落 /opt/data/cache/<peerid>_watch_state.json（冷却/配额/升级用）。
设计原则：监控系统能直达的信号（组网 peer、总线 commit/回执、NAS 日志），不爬群（bot 读群被 230027 拦）。
"""
import json, re, subprocess, sys, time, pathlib, datetime, os

CHAT = os.environ.get("WATCH_CHAT", "oc_568730200f9a3120919be177344687e5")
QUEEN = "ou_b172b28aa8416f7fca826bc151b9cbb8"
NAS = "192.168.199.2"
GITEA_MESH = "100.66.1.7:3000"
WATCH_REPO = pathlib.Path("/opt/data/cache/a2a-bus-watch")
NUDGE_GAP = 4 * 3600
NUDGE_MAX = 3


def sh(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ssh_nas(script, timeout=90):
    return sh(f"ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "
              f"-i /opt/data/.ssh/id_ed25519 DY@{NAS} {json.dumps('sh -s')} <<'EOS'\n{script}\nEOS", timeout)


def mesh_state(peerid, mesh_ip):
    script = (f"sudo -n /usr/bin/docker exec owjdxb sh -c \"grep -aE 'addRoute|RouteAdd' "
              f"/data/store/OWData/owjdxb/.ownbsv/NodeBabyLinkService.log | grep -a {peerid} "
              f"| tail -1 | grep -oE '100[.]66[.]1[.][0-9]+' | tail -1\"; "
              f"curl -s -m5 -o /dev/null -w 'nblink=%{{http_code}} ' http://{mesh_ip}:16880/; "
              f"curl -s -m5 -o /dev/null -w 'gitea=%{{http_code}}\\n' http://{GITEA_MESH}/api/v1/version")
    rc, out = ssh_nas(script)
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    peer_line = next((l for l in lines if re.match(r"^100\.66\.1\.\d+$", l)), "")
    m = re.search(r"nblink=(\d+)\s+gitea=(\d+)", out)
    return bool(peer_line), (int(m.group(1)) if m else 0), (int(m.group(2)) if m else 0)


def bus_activity(author):
    if not WATCH_REPO.exists():
        sh(f"git clone -q --depth 1 http://{GITEA_MESH}/anc/a2a-bus.git {WATCH_REPO}", 240)
    else:
        sh(f"git -C {WATCH_REPO} fetch -q --depth 1 origin main && git -C {WATCH_REPO} reset -q --hard origin/main", 240)
    if not WATCH_REPO.exists():
        return False, []
    ev = []
    rc, out = sh(f"git -C {WATCH_REPO} log --since='30 hours ago' --format='%an|%s'")
    for l in out.splitlines():
        if author.lower() in l.lower():
            ev.append("commit: " + l[:70])
    rc, out = sh(f"ls -t {WATCH_REPO}/outbox/ 2>/dev/null | grep -i {author} | head -3")
    for f in [x for x in out.splitlines() if x.strip()]:
        ev.append("outbox: " + f)
    return bool(ev), ev[:5]


def nudge(text, to_q=False, openid=None):
    target = QUEEN if to_q else (openid or "")
    if not target:
        return False, "no target"
    rc, out = sh(f'cd /opt/data/memories && python3 ping_jarvis.py {CHAT} {target} {json.dumps(text)}', 90)
    return rc == 0 and "code= 0" in out, out[-160:]


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print("usage: node_link_watch.py <peerid> <mesh_ip> <bus_author> [--openid X] [--chat Y] [--nudge]")
        sys.exit(2)
    peerid, mesh_ip, author = args[0], args[1], args[2]
    openid = None
    do_nudge = False
    global CHAT
    i = 3
    while i < len(args):
        if args[i] == "--openid":
            openid = args[i + 1]; i += 2
        elif args[i] == "--chat":
            CHAT = args[i + 1]; i += 2
        elif args[i] == "--nudge":
            do_nudge = True; i += 1
        else:
            i += 1
    state_f = pathlib.Path(f"/opt/data/cache/{peerid}_watch_state.json")
    now = time.time(); today = datetime.date.today().isoformat()
    peer_ok, nb, gt = mesh_state(peerid, mesh_ip)
    act_ok, ev = bus_activity(author)
    st = {}
    if state_f.exists():
        try:
            st = json.loads(state_f.read_text())
        except Exception:
            pass
    if st.get("nudge_day") != today:
        st["nudge_day"], st["nudge_count"] = today, 0
    print(f"[{datetime.datetime.now():%F %T}] peer={peer_ok} nblink={nb} gitea={gt} bus_active={act_ok} {ev}")
    ok = (nb in (404, 200)) and gt == 200
    if act_ok:
        print("  ✅ 节点活在网络里且总线有活动")
    elif not ok:
        print("  ⚠️ 链路断点：从 NAS 侧查节点小宝日志/peer/白名单/版本定位")
    else:
        print("  ⏳ 组网与服务都通，等节点 clone+sync.sh+PING 回执")
    if do_nudge and not act_ok:
        cooled = now - st.get("last_nudge", 0) > NUDGE_GAP
        quota = st.get("nudge_count", 0) < NUDGE_MAX
        if cooled and quota and openid:
            msg = (f"{author}，进度卡在你这边：组网已通（peer {peerid} → {mesh_ip}），Gitea {GITEA_MESH} 也 200。\n"
                   f"请跑：curl -m5 -o /dev/null -w '%{{http_code}}\\n' http://{GITEA_MESH}/api/v1/version\n"
                   "通了就 clone → sync.sh → push PING 回执 → 群里发「PING <author> ✅」。\n"
                   "哪步报错贴原文（000=组网不通/401=密码/403=没授权），我从 NAS 侧定位。")
            sent, d = nudge(msg, openid=openid); print(f"  📣 nudge sent={sent} {d}")
            if sent:
                st["last_nudge"] = now; st["nudge_count"] = st.get("nudge_count", 0) + 1
        else:
            print(f"  (催办冷却中 count={st.get('nudge_count')})")
        esc = st.get("escalated_at", 0)
        if (now - esc > 24 * 3600) and (now - st.get("last_nudge", 0) > NUDGE_GAP):
            sm = f"【QUEEN·升级】{author} 入列卡 >24h：组网 peer {peerid} 在线、Gitea 200，但总线无近 30h 活动，群内催办无回。"
            sent, d = nudge(sm, to_q=True); print(f"  🚨 escalate sent={sent} {d}")
            if sent:
                st["escalated_at"] = now
    state_f.write_text(json.dumps(st, ensure_ascii=False))


if __name__ == "__main__":
    main()
