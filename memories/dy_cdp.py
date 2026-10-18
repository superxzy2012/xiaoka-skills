#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dy_cdp.py — 抖音入库的 CDP 兜底通道（yt-dlp 403 时用）。

为什么需要它：
  yt-dlp 的抖音提取器要自己签 a_bogus，抖音升级后固定 403
  （Failed to download web detail JSON: HTTP Error 403）。
  换路：不自己签，借用 BOSS 已登录 Chrome 里页面自己的 JS 去签名，
  我们只旁观它的网络响应（Network.getResponseBody）拿 aweme_detail。

对外只暴露一个函数：
    fetch(share_url, workdir) -> (meta_dict, video_path)
失败抛 RuntimeError。
"""
import json
import os
import re
import time
import urllib.request

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import CDP  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
WANT = ("aweme/detail", "aweme/v1/web/aweme/detail")
SCRATCH = "/opt/data/cache/scratch"


def resolve_aweme_id(share_url):
    """短链 → aweme_id（v.douyin.com 302 到 iesdouyin/share/video/<id>）。"""
    req = urllib.request.Request(share_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        final = r.geturl()
    m = re.search(r"/(?:video|note)/(\d+)", final)
    if not m:
        m = re.search(r"(\d{15,})", final)
    if not m:
        raise RuntimeError("解析不出 aweme_id: " + final[:200])
    return m.group(1)


def _capture_detail(aweme_id, wait=25):
    """开 CDP 标签，旁观 aweme/detail 响应。多端点自动故障切换。"""
    import cdp as _cdpmod
    eps = [x for x in [_cdpmod.CDP_URL, "http://192.168.199.2:9222",
                       "http://192.168.199.184:9224"] if x]
    seen, err = [], None
    for ep in eps:
        if ep in seen:
            continue
        seen.append(ep)
        try:
            return _capture_once(aweme_id, ep, wait)
        except Exception as e:
            err = e
    raise err or RuntimeError("所有 CDP 端点均失败")


def _capture_once(aweme_id, ep, wait=25):
    url = f"https://www.douyin.com/video/{aweme_id}"
    hits = []
    with CDP(url=ep) as c:
        c.new_tab("about:blank", background=True)
        c.call("Network.enable", {}, c._sid)
        c.call("Page.navigate", {"url": url}, c._sid)
        t0 = time.time()
        got_at = None
        while time.time() - t0 < wait:
            try:
                c.ws.settimeout(2)
                raw = c.ws.recv()
            except Exception:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get("method") == "Network.responseReceived":
                p = m["params"]
                u = (p.get("response") or {}).get("url", "")
                if any(w in u for w in WANT):
                    hits.append(p["requestId"])
                    if got_at is None:
                        got_at = time.time()
            # 命中后再收 1.5s 兜底（同一条常有多份响应），然后立刻收工。
            # 旧版死等到 wait=25s，导致每次解析固定 26s —— 这是全链路最大的假耗时。
            if got_at and time.time() - got_at > 1.5:
                break
        detail = None
        for rid in hits:
            try:
                r = c.call("Network.getResponseBody", {"requestId": rid}, c._sid)
                res = r.get("result") or {}
                body = res.get("body")
                if not body:
                    continue
                if res.get("base64Encoded"):
                    import base64
                    body = base64.b64decode(body).decode("utf-8", "replace")
                d = json.loads(body)
                if isinstance(d, dict) and d.get("aweme_detail"):
                    detail = d["aweme_detail"]
                    break
            except Exception:
                continue
        c.close_tab()
    if not detail:
        raise RuntimeError(f"CDP 未截到 aweme/detail（命中 {len(hits)} 条）")
    return detail


def _best_url(a):
    """挑无水印直链：play_addr（无水印）> download_addr（带水印）。"""
    v = a.get("video") or {}
    for key in ("play_addr", "play_addr_h264", "play_addr_265", "download_addr"):
        ul = ((v.get(key) or {}).get("url_list")) or []
        ul = [u for u in ul if u.startswith("http")]
        if ul:
            return ul[0], key
    # bit_rate 兜底
    for b in (v.get("bit_rate") or []):
        ul = ((b.get("play_addr") or {}).get("url_list")) or []
        ul = [u for u in ul if u.startswith("http")]
        if ul:
            return ul[0], "bit_rate"
    raise RuntimeError("aweme_detail 里没有可用的播放直链")


def _download(url, dest, referer="https://www.douyin.com/"):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer, "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest)


def fetch(share_url, workdir):
    """→ (meta, video_path)。meta 字段与 ingest.fetch_meta 对齐。"""
    os.makedirs(workdir, exist_ok=True)
    aid = resolve_aweme_id(share_url)
    a = _capture_detail(aid)
    src, which = _best_url(a)
    dest = os.path.join(workdir, f"{aid}.mp4")
    size = _download(src, dest)
    if size < 10000:
        raise RuntimeError(f"下载文件过小（{size}B），直链可能已过期")
    au = a.get("author") or {}
    meta = {
        "id": str(a.get("aweme_id") or aid),
        "title": a.get("desc") or "",
        "author": au.get("nickname") or "",
        "duration": round((a.get("duration") or 0) / 1000, 1),
        "sec_uid": au.get("sec_uid") or "",
        "src_key": which,
        "statistics": a.get("statistics") or {},
        "create_time": a.get("create_time"),
    }
    # 供调试
    try:
        json.dump(a, open(os.path.join(SCRATCH, f"dy_detail_{aid}.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return meta, dest


if __name__ == "__main__":
    import sys as _s
    u = _s.argv[1]
    wd = _s.argv[2] if len(_s.argv) > 2 else os.path.join(SCRATCH, "dy_test")
    m, p = fetch(u, wd)
    print(json.dumps(m, ensure_ascii=False, indent=1))
    print("video:", p, os.path.getsize(p) // 1024, "KB")
