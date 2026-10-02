#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音登录二维码截图 · 持久 profile
用法: python3 douyin_login.py [--qr-only]
"""
import sys, time, os
from playwright.sync_api import sync_playwright

PROFILE = "/opt/data/browser-profile"
os.makedirs(PROFILE, exist_ok=True)
OUT = "/opt/data/cache/scratch"
os.makedirs(OUT, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  "--disable-dev-shm-usage"],
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)

        # 关掉可能的弹窗
        for sel in ['div[class*="dy-account-close"]', 'span[class*="close"]',
                    'div[data-e2e="login-close"]']:
            try:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click(timeout=2500)
                    time.sleep(1)
            except Exception:
                pass

        # 找登录入口
        for sel in ['#login-panel-new', 'div[id*="login"]', 'text=登录']:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    el.click(timeout=3000)
                    print(f"点击登录入口: {sel}")
                    time.sleep(5)
                    break
            except Exception:
                pass

        time.sleep(4)
        full = f"{OUT}/douyin_login_full.png"
        page.screenshot(path=full, full_page=False)
        print(f"整页截图: {full}")

        # 裁出登录弹窗区域
        box = None
        for sel in ['#login-pannel', '#login-panel-new', 'div[class*="login-panel"]',
                    'div[class*="account"]', '#douyin-header-menuCt03']:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    box = el.bounding_box()
                    if box and box["width"] > 200:
                        print(f"找到登录框: {sel} box={box}")
                        break
            except Exception:
                pass

        if box:
            pad = 20
            qr = f"{OUT}/douyin_qrcode.png"
            page.screenshot(path=qr, clip={
                "x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
                "width": min(1280, box["width"] + pad * 2),
                "height": min(900, box["height"] + pad * 2)})
            print(f"二维码截图: {qr}")
        else:
            print("未定位到登录框，用整页截图")

        # 检查登录状态
        cookies = browser.cookies()
        names = [c["name"] for c in cookies]
        logged = any(n in names for n in ("sessionid", "sessionid_ss", "sid_tt", "passport_csrf_token"))
        print(f"Cookie 数: {len(cookies)}  已登录: {logged}")
        print("关键 cookie:", [n for n in names if n in
              ("sessionid", "sessionid_ss", "sid_tt", "ttwid", "passport_csrf_token", "uid_tt")])

        browser.close()
        return 0

if __name__ == "__main__":
    sys.exit(main())
