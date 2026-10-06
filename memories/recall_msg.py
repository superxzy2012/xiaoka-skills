#!/usr/bin/env python3
"""撤回自己刚发的测试消息，避免刷屏。"""
import json
import sys
import urllib.request

sys.path.insert(0, "/opt/data/memories")
from ping_jarvis import load_env, tenant_token  # noqa: E402


def recall(token, message_id):
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages/" + message_id,
        data=b"{}",
        method="DELETE",
        headers={"Authorization": "Bearer " + token},
    )
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def main():
    token = tenant_token(load_env())
    for mid in sys.argv[1:]:
        out = recall(token, mid)
        print(mid, "->", out.get("code"), out.get("msg"))


if __name__ == "__main__":
    main()