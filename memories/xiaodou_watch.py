#!/usr/bin/env python3
"""小豆入列看门狗：查组网 peer / Gitea 可达 / 总线 PING 回执，卡住则群里 @小豆 催一次。
状态落 /opt/data/cache/xiaodou_watch_state.json，避免刷屏。
用法: python3 xiaodou_watch.py [--nudge]   (不带 --nudge 只体检不发群)"""
import json, re, subprocess, sys, time, urllib.request, pathlib, datetime, base64, os

CHAT = "oc_568730200f9a3120919be177344687e5"
XIAODOU_OPENID = "ou_4b8b06fc47ac1a6372bae51f01aebbd4"
PEER = "9595DAD2AA42636BOW"
MESH_IP = "100.66.1.9"
WATCH_REPO = pathlib.Path("/opt/data/cache/a2a-bus-watch")
STATE = pathlib.Path("/opt/data/cache/xiaodou_watch_state.json")
NUDGE_GAP = 4 * 3600      # 两次催办最小间隔
NUDGE_MAX_PER_DAY = 3

def sh(cmd, timeout=60):
    # 远端 PowerShell 会吐 GBK，统一容错解码，避免 UnicodeDecodeError 打断看门狗
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
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

def xiaodou_log_check(minutes=30):
    """小豆侧模型健康：近 N 分钟 errors.log 里 404/模型不存在 次数 + agent.log 成功回合数。
    返回 dict 或 None（SSH 不可达）。用既有 worker SSH 通道（xiaodou-win → 43.153.26.131）。"""
    ps = r'''
$h="C:\Users\Administrator\AppData\Local\hermes\logs"
$since=(Get-Date).AddMinutes(-__MIN__)
$n404=0; $last404=""
$f="$h\errors.log"
if(Test-Path $f){
  Get-Content $f -Tail 4000 -Encoding UTF8 | ForEach-Object {
    $l=$_
    if($l -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'){
      $t=[datetime]::ParseExact($matches[1],'yyyy-MM-dd HH:mm:ss',$null)
      if($t -ge $since -and $l -match '404|模型不存在'){ $script:n404++; $script:last404=$l }
    }
  }
}
$nok=0; $lastok=""
$f2="$h\agent.log"
if(Test-Path $f2){
  Get-Content $f2 -Tail 4000 -Encoding UTF8 | ForEach-Object {
    $l=$_
    if($l -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'){
      $t=[datetime]::ParseExact($matches[1],'yyyy-MM-dd HH:mm:ss',$null)
      if($t -ge $since -and $l -match 'Turn ended'){ $script:nok++; $script:lastok=$l }
    }
  }
}
$nin=0; $lastin=""
$f3="$h\gateway.log"
$graceEnd=(Get-Date).AddMinutes(-10)
if(Test-Path $f3){
  Get-Content $f3 -Tail 4000 -Encoding UTF8 | ForEach-Object {
    $l=$_
    if($l -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'){
      $t=[datetime]::ParseExact($matches[1],'yyyy-MM-dd HH:mm:ss',$null)
      if($t -ge $since -and $t -le $graceEnd -and $l -match 'inbound message:|Inbound group message received'){
        $script:nin++; $script:lastin=$l
      }
    }
  }
}
Write-Output ("N404=" + $n404 + "|NOK=" + $nok + "|NIN=" + $nin)
if($last404){ Write-Output ("LAST404=" + $last404.Substring(0,[Math]::Min(200,$last404.Length))) }
if($lastok){ Write-Output ("LASTOK=" + $lastok.Substring(0,[Math]::Min(160,$lastok.Length))) }
if($lastin){ Write-Output ("LASTIN=" + $lastin.Substring(0,[Math]::Min(160,$lastin.Length))) }
'''.replace("__MIN__", str(minutes))
    b64 = base64.b64encode(ps.encode("utf-16-le")).decode()
    rc, out = sh(f'ssh -o BatchMode=yes -o ConnectTimeout=15 xiaodou-win '
                 f'"powershell -NoProfile -EncodedCommand {b64}"', 120)
    m = re.search(r"N404=(\d+)\|NOK=(\d+)\|NIN=(\d+)", out)
    if rc != 0 or not m:
        return None
    last404 = next((l[8:] for l in out.splitlines() if l.startswith("LAST404=")), "")
    lastin = next((l[7:] for l in out.splitlines() if l.startswith("LASTIN=")), "")
    return {"n404": int(m.group(1)), "nok": int(m.group(2)),
            "nin": int(m.group(3)), "last404": last404, "lastin": lastin}


def judge_model_health(mh):
    """模型/通道健康判定表（纯函数，便于单测）。
    mh: {n404, nok, nin} 或 None（SSH 不可达）
    返回 (状态码, 人话说明)
      ok          正常
      unreachable SSH 不可达 → 不判、不告警（避免把关机当故障）
      model_404   有 404 且窗口内 0 成功回合 → 模型路由故障
      silent      有入站消息、0 成功回合、0 次 404 → 通道静默（网关挂死/hang）
      idle        无入站、无回合 → 没人找他，不算故障
      degraded    有 404 但仍有成功回合 → 记录不告警（部分降级）
    """
    if mh is None:
        return "unreachable", "SSH 不可达，模型健康不可判"
    n404, nok, nin = mh["n404"], mh["nok"], mh.get("nin", 0)
    if n404 > 0 and nok == 0:
        return "model_404", f"近窗 {n404} 次 404 且 0 成功回合 ⇒ 模型路由故障"
    if n404 > 0:
        return "degraded", f"近窗 {n404} 次 404 但仍有 {nok} 次成功回合 ⇒ 部分降级，不告警"
    if nin > 0 and nok == 0:
        return "silent", f"近窗 {nin} 条入站消息但 0 成功回合、0 次 404 ⇒ 通道静默（疑网关挂死）"
    if nin == 0 and nok == 0:
        return "idle", "近窗无入站消息、无回合 ⇒ 无人找他，正常"
    return "ok", f"近窗 入站={nin} 成功回合={nok} 404={n404}"


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"last_nudge": 0, "nudge_day": "", "nudge_count": 0}

def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False))

ALERT_CFG = pathlib.Path(os.environ.get("WATCHDOG_ALERT_CFG",
                                        "/opt/data/state/watchdog_alert_targets.json"))
BOSS_OPENID = "ou_ce4e47d4a84858d6d7e64c1a2cdda402"   # 2026-10-28 经 members 接口实测
QUEEN_OPENID = "ou_b172b28aa8416f7fca826bc151b9cbb8"
QUEEN_OFFLINE_FROM = "2026-10-30"   # QUEEN 下线日：此日后兜底不许再指向她


def _fallback_target(today):
    """兜底接收人（QUEEN 2026-10-28 D1：三处兜底原先全退回 QUEEN，
    而 10-30 起 QUEEN 就是「没人」——配置丢/日期写错时恰好落进零覆盖且不报错）。
    改为按日期：10-30 起兜底 BOSS（唯一常在线人类），之前兜底 QUEEN。
    """
    if today >= QUEEN_OFFLINE_FROM:
        return [("BOSS", BOSS_OPENID)]
    return [("QUEEN", QUEEN_OPENID)]


def load_alert_targets(today=None):
    """按日期解析告警接收人（QUEEN 2026-10-28 P2-1：接收人必须配置化，
    否则 10-30 QUEEN 下线后 silent 告警无人接收、覆盖归零）。
    返回 (targets, warnings)：targets = [(name, open_id)]，已剔除未绑定项。
    """
    warnings = []
    today = today or datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        cfg = json.loads(ALERT_CFG.read_text(encoding="utf-8"))
    except Exception as ex:
        warnings.append(f"告警配置读不到({ex})，按日期兜底")
        return _fallback_target(today), warnings
    best, best_from = None, ""
    for rule in cfg.get("schedule", []):
        f = rule.get("effective_from", "")
        u = rule.get("effective_until", "9999-12-31")
        if f <= today <= u and f >= best_from:
            best, best_from = rule, f
    if not best:
        warnings.append(f"{today} 无匹配规则，按日期兜底")
        return _fallback_target(today), warnings
    out = []
    for t in best.get("targets", []):
        if t.get("open_id"):
            out.append((t.get("name") or "?", t["open_id"]))
        else:
            warnings.append(f"告警目标 {t.get('name')} 未绑定 open_id（小卡 app 视角），已跳过")
    if not out:
        warnings.append("所有目标都未绑定 ⇒ 按日期兜底，宁扰不默")
        out = _fallback_target(today)
    return out, warnings


def nudge(text, to_q=False, targets=None):
    """to_q=True 保留旧语义（@QUEEN）；targets 显式给接收人列表时优先用它，逐个发。"""
    if targets is None:
        targets = [("QUEEN", "ou_b172b28aa8416f7fca826bc151b9cbb8")] if to_q \
            else [("xiaodou", XIAODOU_OPENID)]
    ok_all, detail = True, ""
    for name, oid in targets:
        body = text if len(targets) == 1 else f"{text}\n\n（收件人：{name}）"
        rc, out = sh(f'cd /opt/data/memories && python3 ping_jarvis.py {CHAT} {oid} {json.dumps(body)}', 90)
        ok = rc == 0 and "code= 0" in out
        ok_all = ok_all and ok
        detail += f"[{name}:{'ok' if ok else 'fail'}]"
    return ok_all, detail

def bind_target(name, open_id):
    """把某个告警目标的 open_id 写进配置（QUEEN 2026-10-28 P2-1 的绑定入口）。
    用法: python3 xiaodou_watch.py --bind JARVIS ou_xxx
    """
    cfg = json.loads(ALERT_CFG.read_text(encoding="utf-8"))
    hit = 0
    for rule in cfg.get("schedule", []):
        for t in rule.get("targets", []):
            if (t.get("name") or "").upper() == name.upper():
                t["open_id"] = open_id
                t.pop("note", None)
                hit += 1
    if not hit:
        raise SystemExit(f"配置里没有名为 {name} 的目标，未改动")
    ALERT_CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"bound {name} -> {open_id}（{hit} 条规则）")
    for d in ("2026-10-28", "2026-10-30"):
        print(f"  {d}: {[n for n, _ in load_alert_targets(d)[0]]}")


def main():
    do_nudge = "--nudge" in sys.argv
    if "--bind" in sys.argv:
        i = sys.argv.index("--bind")
        bind_target(sys.argv[i + 1], sys.argv[i + 2])
        return
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

    # ---- 模型健康：近 45 分钟 404 检查（QUEEN 2026-10-28 批，归属小卡）----
    # 窗口 45min > 采样间隔 30min，避免两次采样之间漏掉故障窗口
    # 判定表见 judge_model_health()：model_404 / silent 两种才告警
    mh = xiaodou_log_check(45)
    st["model_health"] = mh
    mstate, mwhy = judge_model_health(mh)
    st["model_state"] = mstate
    icon = {"ok": "✅", "idle": "💤", "degraded": "⚠️", "model_404": "🚨",
            "silent": "🚨", "unreachable": "⚠️"}.get(mstate, "·")
    print(f"  {icon} 模型健康[{mstate}] {mwhy}")
    if mh:
        print(f"     明细: 404={mh['n404']} 成功回合={mh['nok']} 入站={mh.get('nin', 0)}")
        if mh["last404"]:
            print("     last404: " + mh["last404"][:150])
    if mstate in ("model_404", "silent") and do_nudge:
        cooled404 = now - st.get("last_404_alert", 0) > NUDGE_GAP
        if cooled404:
            if mstate == "model_404":
                msg = (f"【告警·模型404】小豆节点近 45 分钟出现 {mh['n404']} 次 404（模型不存在），"
                       f"且期间 0 次成功回合 ⇒ 他很可能又停止出话了。\n"
                       f"最近一条：{mh['last404'][:150]}\n"
                       "排查口径：先 GET 网关 /v1/models 核 config 里 model.default 与 providers.*.model 是否仍在目录内，"
                       "再核 gateway 是否在重启后重读过 config。")
                alert_targets = None  # 模型故障时他网关还活着，@ 他本人
            else:
                msg = ("【告警·通道静默】小豆节点近 45 分钟有入站消息，但 0 次成功回合、也 0 次 404 "
                       "⇒ 不是模型名问题，是网关挂死/卡在模型调用里了（上次 10:35 判单 cron 卡 29 分钟就是这形态）。\n"
                       f"最近一条入站：{(mh.get('lastin') or '')[:130]}\n"
                       "排查口径：核 gateway 进程是否还活着（PID 是否变）、agent.log 末条是否停在某次 API call、"
                       "必要时重启 gateway。")
                # 通道静默时他自己读不到群（网关挂死），@ 他等于白喊 → 走配置的接收人
                alert_targets, cfg_warns = load_alert_targets()
                for w in cfg_warns:
                    print(f"  ⚠️ 告警配置：{w}")
                print("  📮 静默告警收件人: " + ",".join(n for n, _ in alert_targets))
            sent, detail = nudge(msg, to_q=(mstate == "silent"), targets=alert_targets)
            print(f"  📣 {mstate} 告警 sent={sent} {detail}")
            if sent:
                st["last_404_alert"] = now
                st["last_alert_kind"] = mstate
        else:
            print(f"  (告警冷却中 last_404_alert={st.get('last_404_alert')})")

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
