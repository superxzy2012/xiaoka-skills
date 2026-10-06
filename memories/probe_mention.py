#!/usr/bin/env python3
"""探测某个 open_id 在「我的应用视角」下能否被 @ 解析。

飞书 open_id 是应用维度的：BOSS 手里的 ou_xxx 与我发消息时的视角不一定一致。
判定方法：发一条带 <at user_id="..."> 的消息，看 API 返回的 mentions 里
该 id 的 name 字段是否被解析成真实昵称（解析成功才有 name）。

用法: python3 probe_mention.py <chat_id> <open_id> [<open_id> ...]
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/opt/data/memories")
from ping_jarvis import load_env, tenant_token  # noqa: E402

CHAT = "oc_568730200f9a3120919be177344687e5"


def main():
    chat_id = sys.argv[1] if len(sys.argv) > 1 else CHAT
    ids = sys.argv[2:]
    token = tenant_token(load_env())
    ats = "".join('<at user_id="%s"></at> ' % i for i in ids)
    content = json.dumps({"text": ats + "mention probe"}, ensure_ascii=False)
    body = json.dumps(
        {"receive_id": chat_id, "msg_type": "text", "content": content}
    ).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + token,
        },
    )
    res = json.loads(urllib.request.urlopen(req, timeout=20).read())
    print("code=", res.get("code"), res.get("msg"))
    data = res.get("data") or {}
    print("message_id=", data.get("message_id"), " <-- 测完记得撤回")
    got = {m.get("id"): (m.get("name") or "<空>") for m in (data.get("mentions") or [])}
    for i in ids:
        print("%s -> %s" % (i, got.get(i, "NOT-RESOLVED")))


if __name__ == "__main__":
    main()