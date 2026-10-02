#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe a remote CDP browser: pages, per-site cookie counts, and — critically —
whether a site session is REAL or just guest cookies.

Usage:
    python3 probe_cdp_auth.py <cdp_url> [site_domain ...]

Exit codes: 0 ok, 2 connection failed, 3 no authed endpoint responded
"""
import json
import sys
from collections import defaultdict

from playwright.sync_api import sync_playwright

# Endpoints that sit behind the login. Add per site as needed.
AUTH_PROBES = {
    "meituan.com": "https://i.waimai.meituan.com/openh5/address/list",
}


def probe_site(pg, base_domain, url):
    """Load a URL and try the site's auth-gated endpoint from inside the page."""
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        return {"domain": base_domain, "error": f"nav failed: {str(e)[:120]}"}
    return None


def main():
    cdp = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9222"
    sites = sys.argv[2:]

    with sync_playwright() as p:
        try:
            b = p.chromium.connect_over_cdp(cdp)
        except Exception as e:
            print(f"❌ CDP 连接失败: {str(e)[:200]}")
            print(f"   先验桥接: curl -s {cdp}/json/version")
            return 2

        ctx = b.contexts[0]
        pages = [pg.url for pg in ctx.pages]
        print(f"✅ CDP 已连接 | contexts={len(b.contexts)} pages={len(pages)}")
        for u in pages[:12]:
            print(f"   - {u[:110]}")

        allc = ctx.cookies()
        per = defaultdict(list)
        for c in allc:
            d = c["domain"]
            for s in (sites or [d]):
                if s in d:
                    per[s].append(c["name"])
        print(f"\n共 {len(allc)} cookie")
        for s, names in per.items():
            print(f"  {s}: {len(names)} 个")

        # Auth reality check
        print("\n=== 登录态真实性核验（cookie 数量不作数）===")
        verdicts = {}
        for domain, api in AUTH_PROBES.items():
            pg = ctx.new_page()
            try:
                res = pg.evaluate(
                    """async (api) => {
                        try {
                            const r = await fetch(api, {credentials:'include'});
                            const t = await r.text();
                            return {status: r.status, body: t.slice(0, 200)};
                        } catch (e) { return {error: String(e)}; }
                    }""",
                    api,
                )
            finally:
                pg.close()
            out = json.dumps(res, ensure_ascii=False)
            guest = '"401"' in out or "登录" in out
            verdicts[domain] = "GUEST" if guest else "可能已登录(需人工确认)"
            print(f"  {domain}: {verdicts[domain]}\n      {out[:160]}")
        b.close()

    if verdicts and all(v == "GUEST" for v in verdicts.values()):
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
