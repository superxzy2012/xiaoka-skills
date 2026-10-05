#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理 2026-10-04 自检用的临时探针文件。"""
import os

for f in ("_link_probe.py", "_mem_probe.py", "_append_log.py"):
    p = os.path.join("/opt/data/memories", f)
    if os.path.exists(p):
        os.remove(p)
        print("已删除", f)
print("剩余临时文件:", [x for x in os.listdir("/opt/data/memories") if x.startswith("_")])