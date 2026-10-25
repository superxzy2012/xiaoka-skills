#!/usr/bin/env python3
"""飞书桥接自检 + 入站事件隔离探针。

用途：桥接「发出正常但收不到消息」时，把问题切成两半——先证明应用身份/发送权限没问题，
再用最小长连接监听器判定事件到底有没有到达这个 app。

用法（先停掉 NextBridge 主进程，同一 app 不要留两个消费者）：
    set -a && . secrets/feishu_xxx.env && set +a
    export HTTPS_PROXY=http://192.168.199.2:7891 HTTP_PROXY=$HTTPS_PROXY ALL_PROXY=$HTTPS_PROXY
    /opt/data/.venv-browser/bin/python feishu_inbound_probe.py --listen

    # 只做 API 自检（不占长连接）
    /opt/data/.venv-browser/bin/python feishu_inbound_probe.py

    # 顺带往指定会话发一条自检消息，验证 chat_id 与发送权限
    /opt/data/.venv-browser/bin/python feishu_inbound_probe.py --send oc_xxxxxxxx

环境变量：FEISHU_APP_ID / FEISHU_APP_SECRET
"""
import argparse
import asyncio
import json
import os
import sys
import threading
import time
import urllib.request

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE = "https://open.feishu.cn/open-apis"


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def api_selfcheck(send_to: str | None) -> None:
    if not APP_ID or not APP_SECRET:
        sys.exit("缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")

    tok = _req(f"{BASE}/auth/v3/tenant_access_token/internal",
               {"app_id": APP_ID, "app_secret": APP_SECRET})
    print("token:", tok.get("code"), tok.get("msg"), flush=True)
    t = tok.get("tenant_access_token")

    # app_name 是「让用户确认发给哪个机器人」的权威依据
    info = _req(f"{BASE}/application/v6/applications/{APP_ID}?lang=zh_cn", token=t)
    app = (info.get("data") or {}).get("app") or {}
    print("app_name:", app.get("app_name"), flush=True)
    print("callback_info:", json.dumps(app.get("callback_info") or {}, ensure_ascii=False), flush=True)

    # 私聊机器人这里返回空列表属正常，不代表权限缺失
    chats = _req(f"{BASE}/im/v1/chats?page_size=20", token=t)
    items = ((chats.get("data") or {}).get("items")) or []
    print(f"chats: {len(items)} 个（私聊机器人为 0 属正常）", flush=True)
    for c in items:
        print("  chat:", c.get("chat_id"), c.get("name"), flush=True)

    if send_to:
        msg = _req(
            f"{BASE}/im/v1/messages?receive_id_type=chat_id",
            {"receive_id": send_to, "msg_type": "text",
             "content": json.dumps({"text": "【桥接自检】发送通道正常"}, ensure_ascii=False)},
            token=t,
        )
        ok = msg.get("code") == 0
        print("send:", "OK" if ok else f"FAIL {msg.get('code')} {msg.get('msg')}", flush=True)
        if ok:
            print("message_id:", (msg.get("data") or {}).get("message_id"), flush=True)


def listen(seconds: int) -> None:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

    def on_msg(data: P2ImMessageReceiveV1) -> None:
        ev = data.event
        m = ev.message
        try:
            text = json.loads(m.content).get("text", "")
        except Exception:
            text = str(m.content)
        print(f"EVENT chat_id={m.chat_id} type={m.message_type} text={text!r} "
              f"sender={ev.sender.sender_id.open_id}", flush=True)

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_msg)
        .build()
    )

    def run() -> None:
        # lark-oapi 的 ws client 需要一个独立 loop，且要 patch 模块级引用
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        import lark_oapi.ws.client as _ws
        _ws.loop = loop
        ws = lark.ws.Client(APP_ID, APP_SECRET, event_handler=handler, auto_reconnect=True)
        print("LISTENER-START（现在让用户在目标会话发一条消息）", flush=True)
        ws.start()

    threading.Thread(target=run, daemon=True).start()
    time.sleep(seconds)
    print("LISTENER-TIMEOUT", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", metavar="CHAT_ID", help="往该 chat_id 发一条自检消息")
    ap.add_argument("--listen", action="store_true", help="启动最小长连接监听器")
    ap.add_argument("--seconds", type=int, default=300)
    a = ap.parse_args()
    if not a.listen or a.send:
        api_selfcheck(a.send)
    if a.listen:
        listen(a.seconds)
