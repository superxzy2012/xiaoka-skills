#!/usr/bin/env python3
"""Provision a NAS Gitea account + grant write on a repo. Re-run safe (409 = exists).
Password goes to a 600 creds file, never printed. No chat/group output.
Usage: python3 provision_account.py <login> <owner>/<repo> [email]
"""
import base64, json, os, secrets, string, subprocess, sys

GITEA = "http://192.168.199.2:3000"
CURLRC = "/opt/data/cache/scratch/.curlrc.tmp"   # admin user:pass, mode 600
CREDS = "/opt/data/secrets/a2a-bus-creds.txt"

login = sys.argv[1]
repo = sys.argv[2]                                # e.g. anc/a2a-bus
email = sys.argv[3] if len(sys.argv) > 3 else f"{login}@a2a.local"

with open(CURLRC) as f:
    auth = f.read().strip().split("=", 1)[1].strip().strip('"')
b64 = base64.b64encode(auth.encode()).decode()


def api(method, path, payload=None):
    args = ["curl", "-s", "-m", "20", "-X", method, GITEA + path,
            "-H", "Content-Type: application/json", "-H", "Authorization: Basic " + b64,
            "-w", "\n%{http_code}"]
    if payload is not None:
        args += ["-d", json.dumps(payload)]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    body, _, code = out.rpartition("\n")
    return (int(code) if code.isdigit() else 0), (json.loads(body) if body.strip() else {})


pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
c, r = api("POST", "/api/v1/admin/users", {
    "username": login, "email": email, "password": pw,
    "must_change_password": False, "send_notify": False, "source_id": 0})
print(f"create {login}: HTTP {c} {r.get('login') or r.get('message')}")

c2, r2 = api("PUT", f"/api/v1/repos/{repo}/collaborators/{login}", {"permission": "write"})
print(f"grant write: HTTP {c2} {r2.get('message', 'ok')}")

if c in (201, 409) and c2 in (204, 200):
    cur = open(CREDS).read() if os.path.exists(CREDS) else ""
    if login not in cur:
        with open(CREDS, "a") as f:
            f.write(f"{login}\t{pw}\t{repo}\twrite\n")
        os.chmod(CREDS, 0o600)
    print("creds ->", CREDS, "(600)")
else:
    print("!! account/grant failed; creds NOT written")
    sys.exit(1)
