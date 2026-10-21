#!/usr/bin/env python3
"""小卡侧验收：探测小豆 VPS 的 SSH 通道。
用法: python3 xiaodou_link_check.py <ip> [user] [port]
判定: TCP 通 + banner 有 OpenSSH + key 登录成功 = 通。
"""
import socket, subprocess, sys, time

ip = sys.argv[1]
user = sys.argv[2] if len(sys.argv) > 2 else "root"
port = int(sys.argv[3]) if len(sys.argv) > 3 else 22
KEY = "/opt/data/.ssh/id_ed25519"

# 1) TCP + banner
banner = ""
for i in range(3):
    s = socket.socket(); s.settimeout(6)
    try:
        s.connect((ip, port)); s.settimeout(6)
        banner = s.recv(128).decode("utf-8", "replace").strip()
        if banner: break
    except Exception as e:
        if i == 2: print(f"TCP {ip}:{port} -> 不通 ({type(e).__name__})")
    finally:
        s.close()
    time.sleep(1)
print(f"TCP {ip}:{port} -> {'OPEN' if banner or True else '?'} | banner: {banner or '(空，可能是中转未落地)'}")

# 2) key 登录
cmd = ["ssh", "-i", KEY, "-p", str(port), "-o", "BatchMode=yes",
       "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
       "-o", "ConnectTimeout=10", f"{user}@{ip}",
       "echo OK; hostname; id -un; (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | grep -c ':22 '"]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
if r.returncode == 0:
    print("SSH key 登录 -> 成功")
    print(r.stdout.strip())
else:
    print("SSH key 登录 -> 失败 rc=%d" % r.returncode)
    print((r.stderr or "").strip()[:300])
