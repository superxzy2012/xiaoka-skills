import os, datetime, re

BASE = "/opt/nas/volume2/2-AI/obsidian_vault/12-知识星球"
now = datetime.datetime.now()
print("now: %s\n" % now.strftime("%Y-%m-%d %H:%M"))

for g in ["Workbuddy一人公司营", "AI创收私研社"]:
    d = os.path.join(BASE, g, "2026-10")
    if not os.path.isdir(d):
        print("%s: MISSING %s" % (g, d))
        continue
    rows = []
    for n in sorted(os.listdir(d)):
        if not n.endswith(".md"):
            continue
        full = os.path.join(d, n)
        ts = datetime.datetime.fromtimestamp(os.path.getmtime(full))
        rows.append((ts, n))
    rows.sort(reverse=True)
    print("== %s /2026-10  (%d files) ==" % (g, len(rows)))
    for ts, n in rows[:5]:
        print("   %s  %s" % (ts.strftime("%m-%d %H:%M"), n[:64]))
    today = [r for r in rows if r[0].date() == now.date()]
    print("   -> written today: %d\n" % len(today))