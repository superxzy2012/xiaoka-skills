#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音登录框探测：dump DOM 结构，定位二维码元素"""
import time, os, json
from playwright.sync_api import sync_playwright

PROFILE = "/opt/data/browser-profile"
OUT = "/opt/data/cache/scratch"

with sync_playwright() as p:
    b = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE, headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        viewport={"width": 1440, "height": 900}, locale="zh-CN")
    pg = b.pages[0] if b.pages else b.new_page()
    pg.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)

    print("URL:", pg.url)
    print("TITLE:", pg.title())
    body = pg.inner_text("body")[:800]
    print("\n--- 页面可见文本（前800字）---")
    print(body)

    print("\n--- 找 canvas / img（二维码通常是 canvas）---")
    els = pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll('canvas, img[class*="qr"], img[class*="code"], div[class*="qrcode"], div[class*="QR"]').forEach(e => {
            const r = e.getBoundingClientRect();
            if (r.width > 30 && r.height > 30) out.push({
                tag: e.tagName, cls: (e.className||'').toString().slice(0,60),
                x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)});
        });
        return out;
    }""")
    for e in els:
        print(json.dumps(e, ensure_ascii=False))

    print("\n--- 找登录相关容器 ---")
    cands = pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll('div,section,span').forEach(e => {
            const t = (e.innerText||'').trim();
            if (!t || t.length > 30) return;
            if (/扫码登录|验证码登录|密码登录|手机号登录|登录/.test(t)) {
                const r = e.getBoundingClientRect();
                if (r.width > 100 && r.height > 50) out.push({
                    tag: e.tagName, id: e.id, cls: (e.className||'').toString().slice(0,70),
                    text: t.slice(0,30), x: Math.round(r.x), y: Math.round(r.y),
                    w: Math.round(r.width), h: Math.round(r.height)});
            }
        });
        return out.slice(0, 15);
    }""")
    for e in cands:
        print(json.dumps(e, ensure_ascii=False))

    b.close()
