#!/usr/bin/env python3
"""SWARM-SMOKE-20261018：轮询 A2A inbox 里 to=xiaoka 的冒烟任务。

落袋为准：
1. 轮询 inbox/task_SWARM-SMOKE-20261018_*.json，找 to=xiaoka
2. 去重：processed/ 已有同名，或 outbox 已有该 task_ref 的 PING 终态回执 -> 跳过
3. 写 receipt 到 outbox/（status=PING）
4. 移动 task 到 processed/
"""
import glob
import json
import os
import shutil
import sys
import time

ROOT = "/opt/nas/volume2/2-AI/A2A"
INBOX = os.path.join(ROOT, "inbox")
OUTBOX = os.path.join(ROOT, "outbox")
PROCESSED = os.path.join(ROOT, "processed")
ME = "xiaoka"
REF_PREFIX = "SWARM-SMOKE-20261018"
DEADLINE_S = int(sys.argv[1]) if len(sys.argv) > 1 else 420


def now_bj():
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def already_receipted(task_ref):
    for rp in glob.glob(os.path.join(OUTBOX, "receipt_*.json")):
        try:
            d = json.load(open(rp, encoding="utf-8"))
        except Exception:
            continue
        if d.get("task_ref") == task_ref and d.get("from") == ME and d.get("status") == "PING":
            return rp
    return None


def handle(path):
    with open(path, encoding="utf-8") as f:
        task = json.load(f)
    ref = task.get("task_ref", "")
    to = task.get("to", "")
    name = os.path.basename(path)
    print(f"[found] {name} to={to} ref={ref}")
    if to != ME:
        print(f"  -> 不是给我的（to={to}），跳过")
        return False
    if REF_PREFIX not in ref:
        print(f"  -> ref 不含 {REF_PREFIX}，跳过")
        return False
    # 去重
    if os.path.exists(os.path.join(PROCESSED, name)):
        print("  -> processed/ 已有同名，跳过（去重）")
        return True
    ex = already_receipted(ref)
    if ex:
        print(f"  -> 已有终态回执 {os.path.basename(ex)}，跳过（去重）")
        shutil.move(path, os.path.join(PROCESSED, name))
        return True
    # 写 PING 回执
    stamp = now_bj().replace(":", "").replace("-", "")[:15]
    receipt = {
        "receipt_id": f"R-{ref}-{ME}",
        "task_ref": ref,
        "from": ME,
        "to": task.get("from", "friday"),
        "ts": now_bj(),
        "status": "PING",
        "note": "xiaoka NAS container A2A bus write ok",
    }
    rpath = os.path.join(OUTBOX, f"receipt_{ref}_{ME}_{stamp}.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False)
    print(f"[receipt] {rpath}")
    # 移动任务
    shutil.move(path, os.path.join(PROCESSED, name))
    print(f"[moved] inbox -> processed/{name}")
    return True


def main():
    start = time.time()
    done = False
    while time.time() - start < DEADLINE_S:
        hits = sorted(glob.glob(os.path.join(INBOX, f"task_{REF_PREFIX}_*.json")))
        for p in hits:
            if handle(p):
                done = True
        if done:
            print("RESULT=DONE")
            return 0
        print(f"[wait] inbox 暂无 {REF_PREFIX} 给 {ME} 的任务，"
              f"已等 {int(time.time()-start)}s ...")
        time.sleep(15)
    print("RESULT=TIMEOUT")
    return 2


if __name__ == "__main__":
    sys.exit(main())
