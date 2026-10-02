import os, re, collections, datetime

ROOT = "/opt/nas/volume2/2-AI/obsidian_vault/12-知识星球"
if not os.path.isdir(ROOT):
    raise SystemExit("VAULT MISSING: %s" % ROOT)

for group in sorted(os.listdir(ROOT)):
    gpath = os.path.join(ROOT, group)
    if not os.path.isdir(gpath):
        continue
    files, no_id, ids = [], [], []
    for dirpath, _, names in os.walk(gpath):
        for n in names:
            if not n.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, n), gpath)
            files.append(rel)
            m = re.match(r"^(\d{10,})", n)
            if m:
                ids.append(m.group(1))
            else:
                no_id.append(rel)

    dup = [t for t, c in collections.Counter(ids).items() if c > 1]
    by_month = collections.Counter(f.split(os.sep)[0] for f in files)

    print("== %s ==" % group)
    print("  files=%d  unique_topic_ids=%d  dup_ids=%d  no_id_files=%d"
          % (len(files), len(set(ids)), len(dup), len(no_id)))
    print("  by month: %s" % dict(sorted(by_month.items())))
    if dup:
        print("  DUP IDS (first 5): %s" % dup[:5])
    for r in no_id[:5]:
        print("  NO-ID: %s" % r)
    if files:
        newest = max(files, key=lambda f: os.path.getmtime(os.path.join(gpath, f)))
        ts = os.path.getmtime(os.path.join(gpath, newest))
        print("  newest mtime: %s -> %s"
              % (newest, datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")))
    print()