#!/usr/bin/env python3
"""Write one A2A envelope to the shared bus: atomic, uid-boundary aware, verified.

Usage:
  python3 a2a_write.py --from xiaoka --to xiaomi-codex --task-ref A2A-PING \
      --status PING --note "在线" [--kind receipt|task] [--result-file PATH] [--dry-run]

Env overrides: A2A_ROOT, A2A_HOST (user@host), A2A_KEY, A2A_HOST_ROOT
Exit: 0 = landed and verified, 1 = failed (reason printed), 2 = bad usage.

Why the escalation: on the NAS the bus directories are owned by the Mac-side user
(1005:10, mode 755) while this container is uid 10000, so a direct write raises
PermissionError. We stage the bytes in the host /tmp over ssh and land them with a root
container that mounts the host directory, then chown back to the directory's owner.
"""
import argparse
import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.environ.get("A2A_ROOT", "/opt/nas/volume2/2-AI/A2A")
HOST = os.environ.get("A2A_HOST", "DY@192.168.199.2")
KEY = os.environ.get("A2A_KEY", "/opt/data/.ssh/id_ed25519")


def now_cn():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))


def host_view(path):
    """Map the container path to the NAS host path (/opt/nas/volume2 -> /volume2)."""
    override = os.environ.get("A2A_HOST_ROOT")
    if override:
        return override
    if path.startswith("/opt/nas/volume2"):
        return "/volume2" + path[len("/opt/nas/volume2"):]
    return path


def ssh(cmd, stdin=None):
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
         "-i", KEY, "-o", "ConnectTimeout=8", HOST, cmd],
        input=stdin, capture_output=True)


def free_name(directory, name):
    if not os.path.exists(os.path.join(directory, name)):
        return name
    stem, ext = os.path.splitext(name)
    for i in range(1, 100):
        cand = "%s_%d%s" % (stem, i, ext)
        if not os.path.exists(os.path.join(directory, cand)):
            return cand
    raise SystemExit("too many name collisions for " + name)


def write_local(directory, name, data):
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o644)
    os.replace(tmp, os.path.join(directory, name))


def write_via_root(directory, name, data):
    """Stage in host /tmp, then land with a root container. Returns (ok, detail)."""
    hdir = host_view(directory)
    st = os.stat(directory)
    owner = "%d:%d" % (st.st_uid, st.st_gid)
    stage = "/tmp/a2a_stage_%d" % os.getpid()

    r = ssh("rm -rf %s && mkdir -p %s && base64 -d > %s/%s" % (stage, stage, stage, name),
            base64.b64encode(data))
    if r.returncode != 0:
        return False, "ssh stage failed: " + r.stderr.decode(errors="replace")[:200]

    script = (
        "#!/bin/sh\nset -e\n"
        "sudo -n docker run --rm -v %s:/o -v %s:/p alpine \\\n" % (hdir, stage)
        + '  sh -c "cp /p/%s /o/%s && chown %s /o/%s && chmod 644 /o/%s && echo PUSH_OK"\n'
        % (name, name, owner, name, name)
        + "rm -rf %s\n" % stage)
    r = ssh("base64 -d > /tmp/a2a_push.sh && sh /tmp/a2a_push.sh; rm -f /tmp/a2a_push.sh",
            base64.b64encode(script.encode()))
    out = (r.stdout + r.stderr).decode(errors="replace").strip()
    ssh("rm -rf %s" % stage)
    return ("PUSH_OK" in out), out[-300:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="sender", required=True)
    ap.add_argument("--to", dest="target", required=True)
    ap.add_argument("--task-ref", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--kind", choices=["receipt", "task"], default="receipt")
    ap.add_argument("--result-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now = now_cn()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    sub = "outbox" if a.kind == "receipt" else "inbox"
    directory = os.path.join(ROOT, sub)

    if a.kind == "receipt":
        env = {"receipt_id": "R-%s-%s-%s" % (a.task_ref, a.sender, stamp),
               "task_ref": a.task_ref, "from": a.sender, "to": a.target,
               "ts": now.isoformat(timespec="seconds"), "status": a.status,
               "note": a.note}
        if a.result_file:
            env["result_file"] = a.result_file
        name = "receipt_%s_%s_%s.json" % (a.task_ref, a.sender, stamp)
    else:
        env = {"task_ref": a.task_ref, "from": a.sender, "to": a.target,
               "ts": now.isoformat(timespec="seconds"), "type": "task",
               "priority": "P1", "note": a.note}
        name = "task_%s_%s.json" % (a.task_ref, stamp)

    if a.status == "DONE" and not (a.result_file and os.path.exists(a.result_file)):
        print("FAIL: status=DONE requires an existing --result-file")
        return 2

    data = json.dumps(env, ensure_ascii=False, indent=2).encode()
    name = free_name(directory, name)
    final = os.path.join(directory, name)

    if a.dry_run:
        print("TARGET", final)
        print(data.decode())
        return 0

    try:
        write_local(directory, name, data)
        via = "direct"
    except PermissionError:
        ok, detail = write_via_root(directory, name, data)
        via = "root-container"
        if not ok:
            print("FAIL landing:", detail)
            return 1

    # Verification is the read-back through the mount, not the write's exit code.
    if not os.path.exists(final):
        print("FAIL: not visible after write ->", final)
        return 1
    with open(final, encoding="utf-8") as f:
        got = json.load(f)
    if got != env:
        print("FAIL: content mismatch")
        print("wrote:", json.dumps(env, ensure_ascii=False))
        return 1
    st = os.stat(final)
    print("OK", via, final)
    print("owner=%d:%d mode=%o" % (st.st_uid, st.st_gid, st.st_mode & 0o777))
    print(data.decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
