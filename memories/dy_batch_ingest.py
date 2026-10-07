#!/usr/bin/env python3
"""按作品ID 批量入库抖音视频（下载→转写→写 vault），断点续跑。"""
import json, os, subprocess, sys, time, datetime

BASE = "/opt/data/cache/scratch/dy_batch"
PY = "/opt/data/.venv-browser/bin/python"
ING = "/opt/data/memories/ingest.py"
VAULT_TAGS = "学霸妈妈讲AI"
SEC = "MS4wLjABAAAA4ne-HAyUvKW9PkLKE7OOWi6J7R1oVZaJaiWk1-M-vkg"
# 可选：先做作者验证过滤（只抓本号作品）
VERIFY = os.environ.get("DY_VERIFY") == "1"
DROP_EDU = os.environ.get("DY_DROP_EDU") == "1"   # 入库后按【标题】删教育线
import re as _re_mod
VERIFY_JS = r"""
(()=>{
  let sec='';
  for (const a of document.querySelectorAll("a[href*='/user/MS4w']")) {
    const m=(a.getAttribute('href')||'').match(/\/user\/(MS4[A-Za-z0-9_-]+)/);
    if (m && m[1]) { sec=m[1]; break; }
  }
  return JSON.stringify({sec:sec, ttl:(document.title||'').slice(0,100)});
})()
"""

os.makedirs(f"{BASE}/logs", exist_ok=True)
LOGF = f"{BASE}/logs/run.log"


def log(m):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# 🔴 vault 索引缓存：避免每条都 grep 全目录（曾 90s 超时炸掉整个任务）
_IDX = {"path": f"{BASE}/vault_index.json", "mtime": 0, "ids": set()}
_MAP = {}   # douyin_id -> 文件路径


def _load_index():
    """扫描 08-抖音视频学习/*.md 建立 douyin_id -> path 映射。

    🔴 只 glob 目录顶层的 .md，绝不递归——之前的 `grep -rl` 会钻进
    attachments/ 里扫上千张帧图，90 秒超时炸掉整个任务。
    实测 277 个文件全扫 = 0.02 秒，无需再做增量缓存。
    """
    import glob as _g
    D = "/opt/nas/volume2/2-AI/obsidian_vault/08-抖音视频学习"
    ids = set()
    for p in _g.glob(f"{D}/*.md"):
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                head = fh.read(400)
            m = re.search(r'douyin_id: "(\d{19})"', head)
            if m:
                ids.add(m.group(1))
                _MAP[m.group(1)] = p
        except Exception:
            continue
    _IDX["ids"] = ids
    return ids


def already(aweme_id):
    return bool(_load_index() and aweme_id in _IDX["ids"])


def verify_ids(ids):
    """单标签循环验证作者，返回属于本号的 ID 列表 + 标题表。"""
    sys.path.insert(0, "/opt/data/memories")
    from cdp import CDP
    import re as _re
    keep, titles = [], {}
    c = CDP()
    try:
        c.new_tab("about:blank")
        for i, aid in enumerate(ids, 1):
            rec = None
            for _ in (1, 2):
                try:
                    c.goto(f"https://www.douyin.com/video/{aid}", wait=10)
                    raw = c.eval_js(VERIFY_JS)
                    if raw:
                        rec = json.loads(raw if isinstance(raw, str) else raw)
                        break
                except Exception:
                    pass
                time.sleep(3)
            if rec and rec.get("sec") == SEC:
                keep.append(aid)
                titles[aid] = rec.get("ttl", "")
                print(f"    ✅ {aid} {(rec.get('ttl') or '')[:44]}")
            elif rec:
                print(f"    ❌ {aid} 他人作品")
            else:
                print(f"    ⚠️ {aid} 未渲染")
            if i % 10 == 0:
                print(f"    --- {i}/{len(ids)} 已确认 {len(keep)} ---")
            time.sleep(2)
    finally:
        try:
            c.close()
        except Exception:
            pass
    return keep, titles


def find_note_by_id(aid):
    """按 douyin_id 定位笔记文件。

    🔴 不能每条都glob 全目录（500+ 文件 × NAS 磁盘 = 每条数秒）。
    复用 _load_index 的扫描结果，映射 id -> path。
    """
    _load_index()          # 全扫 0.02s，会刷新 _MAP（含刚写入的文件）
    m = _MAP.get(aid)
    return [m] if m else []


def main():
    src = sys.argv[1]
    ids = json.load(open(src))["videos"]
    total = len(ids)
    ok = skip = fail = drop = 0
    errs = []
    titles = {}
    t0 = time.time()
    vc = None
    if VERIFY:
        sys.path.insert(0, "/opt/data/memories")
        from cdp import CDP
        vc = CDP()
        vc.new_tab("about:blank")          # 🔴 唯一标签，全程复用
        log(f"🔍 验证+入库流水（{total} 条）")
    try:
        for i, aid in enumerate(ids, 1):
            if already(aid):
                skip += 1
                continue
            ttl = ""
            if VERIFY:
                rec = None
                for _ in (1, 2):
                    try:
                        vc.goto(f"https://www.douyin.com/video/{aid}", wait=10)
                        raw = vc.eval_js(VERIFY_JS)
                        if raw:
                            rec = json.loads(raw if isinstance(raw, str) else raw)
                            break
                    except Exception:
                        pass
                    time.sleep(3)
                if not rec:
                    log(f"[{i}/{total}] ⚠️ {aid} 未渲染")
                    fail += 1
                    errs.append((aid, "未渲染"))
                    continue
                if rec.get("sec") != SEC:
                    drop += 1
                    continue                     # 🔴 他人作品，直接跳过不抓
                ttl = rec.get("ttl", "")
                titles[aid] = ttl
            url = f"https://www.douyin.com/video/{aid}"
            try:
                r = subprocess.run(
                    [PY, ING, url, "--keyword", VAULT_TAGS],
                    capture_output=True, text=True, timeout=900)
                out = r.stdout or ""
                # 唯一可靠判据：vault 里真的落了笔记
                # 按【文件内容里的 douyin_id】定位，不靠文件名（文件名是标题）
                hit = find_note_by_id(aid)
                # 🔴 只按【文件名/标题】判教育线，绝不扫正文——
                #    正文里有我们写的标注块（含「教育」二字），扫正文会误删技术笔记。
                if hit and DROP_EDU:
                    base = os.path.basename(hit[0])
                    if _re_mod.search(r"Day\s*\d+|青少年|AI素养|十五五|#ai教育|孩子|教学|古诗|语文",
                                      base):
                        os.remove(hit[0])
                        hit = []
                        log(f"[{i}/{total}] 🎓 教育线已剔除 {aid}")
                if hit:
                    ok += 1
                    log(f"[{i}/{total}] ✅ {aid} {ttl[:40]}")
                else:
                    fail += 1
                    err = (r.stderr or out)[-140:].replace("\n", " ")
                    log(f"[{i}/{total}] ❌ {aid} {err}")
                    errs.append((aid, err))
            except subprocess.TimeoutExpired:
                fail += 1
                log(f"[{i}/{total}] ⏱ {aid} 超时")
                errs.append((aid, "timeout"))
            except Exception as e:
                fail += 1
                log(f"[{i}/{total}] ❌ {aid} {type(e).__name__}")
                errs.append((aid, str(e)[:100]))
            if i % 20 == 0:
                el = (time.time() - t0)
                log(f"--- {i}/{total} 入库{ok} 剔除{drop} 失败{fail} "
                    f"用时{el/60:.1f}min 剩{el/i*(total-i)/60:.0f}min ---")
                json.dump(titles, open(f"{BASE}/titles.json", "w"),
                          ensure_ascii=False, indent=1)
            time.sleep(2)
    finally:
        if vc:
            try:
                vc.close()
            except Exception:
                pass
        json.dump(titles, open(f"{BASE}/titles.json", "w"),
                  ensure_ascii=False, indent=1)
    log(f"===== 完成:入库{ok} 已存在{skip} 剔除他人{drop} 失败{fail} / {total} "
        f"用时{(time.time()-t0)/60:.1f}min =====")
    json.dump(errs, open(f"{BASE}/errors.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()