#!/usr/bin/env python3
"""最小飞书长连接监听器 —— 判定「飞书事件到底有没有到」的决定性测试。

用法：
    FEISHU_APP_ID=cli_xxx FEISHU_APP_SECRET=xxx python feishu_ws_probe.py [超时秒数]

判读：
    打印 EVENT chat_id=... text=...  → 飞书侧正常，问题在桥接的驱动/规则
    超时只有 LISTENER-START     → app 层问题（事件订阅 / 权限 / 未发版）

注意：同一 app 的多条长连接会互相抢事件，跑之前先停掉桥接进程。
"""
import os
import sys
import json
import time
import asyncio
import threading

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
TIMEOUT = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def on_message(data: P2ImMessageReceiveV1) -> None:
    try:
        ev = data.event
        msg = ev.message
        try:
            text = json.loads(msg.content).get("text", "")
        except Exception:
            text = str(msg.content)
        print(
            f"EVENT chat_id={msg.chat_id} type={msg.message_type} "
            f"text={text!r} sender={ev.sender.sender_id.open_id}",
            flush=True,
        )
    except Exception as e:  # noqa: BLE001
        print("EVENT-PARSE-ERR", repr(e), flush=True)


handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(on_message)
    .build()
)


def run() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # lark-oapi 的 ws 客户端在模块级持有 loop，必须替换成当前线程的
    import lark_oapi.ws.client as _ws

    _ws.loop = loop
    client = lark.ws.Client(APP_ID, APP_SECRET, event_handler=handler, auto_reconnect=True)
    print("LISTENER-START", flush=True)
    client.start()


threading.Thread(target=run, daemon=True).start()
time.sleep(TIMEOUT)
print("LISTENER-TIMEOUT", flush=True)
