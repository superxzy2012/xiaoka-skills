#!/usr/bin/env python3
"""WhatsApp 扫码配对（neonize）。生成二维码 PNG + 终端 QR，扫码成功后持久化登录态。
用法（后台跑，日志重定向）：
  HTTPS_PROXY=http://192.168.199.2:7891 HTTP_PROXY=... ALL_PROXY=... \
    /opt/data/.venv-browser/bin/python wa_pair_local.py > pair.log 2>&1
成功标志：日志出现 CONNECTED-EVENT 和 LOGIN-PERSISTED。
登录态 DB：/opt/data/cache/scratch/muse_wa/wa_muse_local.db（换路径改 DB 变量）。
"""
import asyncio, os, sys, glob

# 借位加载 libmagic（沙箱无 root，deb 解包到 /opt/data/local/libmagic）
_magic_dir = glob.glob("/opt/data/local/libmagic/usr/lib/*/")
if _magic_dir:
    import ctypes
    try:
        ctypes.CDLL(os.path.join(_magic_dir[0], "libmagic.so.1"))
    except OSError as e:
        print("libmagic load fail:", e, flush=True)

import magic  # noqa: E402
from neonize.aioze.client import NewAClient
from neonize.aioze.events import QREv, PairStatusEv, ConnectedEv

DB = "/opt/data/cache/scratch/muse_wa/wa_muse_local.db"
OUT = "/opt/data/cache/scratch/muse_wa/wa-fresh-qr.png"

async def main():
    client = NewAClient(DB)
    state = {"connected": False}

    @client.event(QREv)
    async def on_qr(evt):
        codes = getattr(evt, "Codes", None)
        if codes:
            raw = list(codes)[-1] if not isinstance(codes, str) else codes
            try:
                import segno
                segno.make(raw, error="M").save(OUT, scale=10, border=4)
                print(f"QR-PNG-SAVED {OUT} len={len(raw)}", flush=True)
            except Exception as e:
                print("QR-RENDER-ERR", e, flush=True)

    @client.event(PairStatusEv)
    async def on_pair(evt):
        print(f"PAIR-STATUS {evt}", flush=True)

    @client.event(ConnectedEv)
    async def on_conn(_e):
        print("CONNECTED-EVENT", flush=True)
        state["connected"] = True

    await client.connect()
    for _ in range(150):  # 5 分钟扫码窗口
        await asyncio.sleep(2)
        if state["connected"]:
            await asyncio.sleep(3)
            print("LOGIN-PERSISTED", flush=True)
            while True:  # 保持进程活着，让调用方决定何时停
                await asyncio.sleep(60)
                print("HEARTBEAT connected=true", flush=True)
    print("TIMEOUT-WAITING", flush=True)

asyncio.run(main())
