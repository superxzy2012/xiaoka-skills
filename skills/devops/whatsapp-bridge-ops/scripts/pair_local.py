#!/usr/bin/env python3
"""本地 WhatsApp 配对：生成新鲜二维码，扫码后持久化登录态到 sqlite。

用法（必须带代理，WhatsApp 握手被墙，直连静默挂死）:
  HTTPS_PROXY=http://192.168.199.2:7891 HTTP_PROXY=... ALL_PROXY=... \
    /opt/data/.venv-browser/bin/python pair_local.py > pair.log 2>&1 &

判定登录: 日志出现 CONNECTED-EVENT / LOGIN-PERSISTED，且 db 文件 >100KB。
重发新码: kill 进程 + rm db + rm png 后重启。
"""
import asyncio, os, sys, glob

# 借位加载 libmagic（neonize import 硬依赖，沙箱无 root 装不了系统包）
_magic_dir = glob.glob("/opt/data/local/libmagic/usr/lib/*/")
if _magic_dir:
    import ctypes
    try:
        ctypes.CDLL(os.path.join(_magic_dir[0], "libmagic.so.1"))
    except OSError as e:
        print("libmagic load fail:", e, flush=True)

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
                print("QR-RENDER-ERR", e, flush=True)  # 兜底: 用 render_qr_from_log.py 转终端码

    @client.event(PairStatusEv)
    async def on_pair(evt):
        print(f"PAIR-STATUS {evt}", flush=True)

    @client.event(ConnectedEv)
    async def on_conn(_e):
        print("CONNECTED-EVENT", flush=True)
        state["connected"] = True

    await client.connect()
    for i in range(150):  # 5 分钟扫码窗口（但单张 QR 只有约 30 秒，超时要重启换码）
        await asyncio.sleep(2)
        if state["connected"]:
            await asyncio.sleep(3)
            print("LOGIN-PERSISTED", flush=True)
            while True:  # 保活，桥接进程可接手
                await asyncio.sleep(60)
                print("HEARTBEAT connected=true", flush=True)
            return
    print("TIMEOUT-WAITING", flush=True)

asyncio.run(main())
