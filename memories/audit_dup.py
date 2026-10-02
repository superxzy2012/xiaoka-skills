import os, re, collections

ROOT = "/opt/nas/volume2/2-AI/obsidian_vault/12-知识星球/Workbuddy一人公司营"
targets = ["82255444148421520", "55522484852115520"]
appledouble = 0

for dirpath, _, names in os.walk(ROOT):
    for n in names:
        if n.startswith("._"):
            appledouble += 1
        if not n.endswith(".md"):
            continue
        for t in targets:
            if n.startswith(t):
                full = os.path.join(dirpath, n)
                print("%s\n   size=%d bytes\n" % (
                    os.path.relpath(full, ROOT), os.path.getsize(full)))

print("AppleDouble (._*) junk files: %d" % appledouble)