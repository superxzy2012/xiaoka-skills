#!/usr/bin/env python3
"""WhatsApp 配对码登录（免扫码）。

用法:
    HTTPS_PROXY=http://192.168.199.2:7891 HTTP_PROXY=$HTTPS_PROXY ALL_PROXY=$HTTPS_PROXY \
      /opt/data/.venv-browser/bin/python pair_code.py <国家码+号码> [db_path]

例: pair_code.py 86【手机号】 /abs/path/wa.db

输出:
    PAIR-CODE-BEGIN XXXX-XXXX PAIR-CODE-END   -> 把码给用户，在
    WhatsApp「设置→已关联设备→关联设备→使用手机号码关联」输入
    CONNECTED-EVENT / LOGIN-PERSISTED          -> 登录成功，登录态已落 db

注意: 同一账号只能有一个 neonize 连接；桥接在跑时先停掉再配对。
"""
import asyncio
import ctypes
import glob
import os
import sys

# --- libmagic 借位（neonize 间接 import magic，缺系统库时必需） ---
for d in glob.glob("/opt/data/local/libmagic/usr/lib/*/"):
    os.environ["LD_LIBRARY_PATH"] = d + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    try:
        ctypes.CDLL(os.path.join(d, "libmagic.so.1"))
    except OSError:
        pass
import magic  # noqa: F401,E402

from neonize.aioze.client import NewAClient  # noqa: E402
from neonize.aioze.events import ConnectedEv, PairStatusEv  # noqa: E402

PHONE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WA_PHONE", "")).strip()
DB = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("WA_DB", "/tmp/wa_pair.db")
if not PHONE:
    sys.exit("usage: pair_code.py <countrycode+number> [db_path]")


async def main() -> None:
    client = NewAClient(DB)
    state = {"connected": False, "requested": False}

    # 关键: QR 必须用 client.event.qr() 注册；@client.event(QREv) 装饰器不会触发
    async def on_qr(_client, _data_qr: bytes) -> None:
        if state["requested"]:
            return
        state["requested"] = True
        print("QR-RECEIVED, requesting pair code...", flush=True)
        try:
            code = await client.PairPhone(PHONE, True)
            print(f"PAIR-CODE-BEGIN {code} PAIR-CODE-END", flush=True)
        except Exception as exc:  # noqa: BLE001
            print("PAIR-CODE-ERR", repr(exc), flush=True)

    client.event.qr(on_qr)

    @client.event(PairStatusEv)
    async def on_pair(_client, evt) -> None:
        print(f"PAIR-STATUS {evt}", flush=True)

    @client.event(ConnectedEv)
    async def on_conn(_client, _evt) -> None:
        print("CONNECTED-EVENT", flush=True)
        state["connected"] = True

    await client.connect()
    for _ in range(240):  # 8 分钟窗口
        await asyncio.sleep(2)
        if state["connected"]:
            await asyncio.sleep(3)
            print("LOGIN-PERSISTED", flush=True)
            while True:  # 保活，登录态已写盘；外部 kill 即可
                await asyncio.sleep(60)
                print("HEARTBEAT connected=true", flush=True)
    print("TIMEOUT-WAITING", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
