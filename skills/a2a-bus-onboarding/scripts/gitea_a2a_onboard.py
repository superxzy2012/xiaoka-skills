#!/usr/bin/env python3
"""Provision + verify an agent account on the shared A2A Gitea bus.

Creates the user (or reuses an existing one), grants write on the bus repo, appends the
credential to the 600 store, and proves access with a real clone + throwaway-branch push
(the branch is deleted afterwards). The password is never printed.

The admin credential is read from the git credential store and matched on USERNAME, not on
host: with many accounts on one Gitea host a host-only match returns some other node's
credential and every admin call fails with 403 "user should be the site admin".

Usage:
  python3 gitea_a2a_onboard.py --login jarvis
  python3 gitea_a2a_onboard.py --login xiaoli --place /opt/nas/volume2/hermes/ancgm-home/secrets/a2a-bus.env
"""
import argparse
import base64
import json
import os
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------- credentials

def read_store(path, admin):
    """Return (user, pass) for `admin` from a git credential store, matching on user."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if "://" not in line or "@" not in line:
                continue
            rest = line.split("://", 1)[1]
            cred, _, _host = rest.rpartition("@")
            user, _, pw = cred.partition(":")
            if urllib.parse.unquote(user) == admin:
                return user, urllib.parse.unquote(pw)
    raise SystemExit(f"no credential for user={admin!r} in {path}")


def api(base, cred, method, path, payload=None):
    url = base.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    token = base64.b64encode(f"{cred[0]}:{cred[1]}".encode()).decode()
    req.add_header("Authorization", "Basic " + token)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


# ------------------------------------------------------------------------ git

def askpass_dir():
    """A 700 dir with an askpass helper; the secret goes through env, not argv."""
    d = tempfile.mkdtemp(prefix="a2a-askpass-")
    p = os.path.join(d, "askpass.sh")
    with open(p, "w") as fh:
        fh.write('#!/bin/sh\ncase "$1" in *[Uu]sername*) echo "$A2A_U";; *) echo "$A2A_P";; esac\n')
    os.chmod(p, 0o700)
    return d, p


def git(args, cwd=None, extra_env=None):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.update(extra_env or {})
    return subprocess.run(["git"] + args, cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=120)


def verify_write(base, repo, login, password, admin_cred):
    """clone + push a temp branch + delete it. Returns 'CLONE_OK PUSH_OK DEL_OK' or a failure tag."""
    url = f"{base.rstrip('/')}/{repo}.git"
    work = tempfile.mkdtemp(prefix="a2a-verify-")
    adir, askpass = askpass_dir()
    env = {"GIT_ASKPASS": askpass, "A2A_U": login, "A2A_P": password}
    branch = f"verify-{login}-{int(time.time())}"
    tags = []
    try:
        r = git(["clone", "-q", "--depth", "1", url, "."], cwd=work, extra_env=env)
        if r.returncode != 0:
            tail = (r.stderr.strip().splitlines() or [""])[-1][:120]
            return "CLONE_FAIL " + tail
        tags.append("CLONE_OK")
        ident = ["-c", "user.email=%s@a2a.local" % login, "-c", "user.name=%s" % login]
        if git(["checkout", "-q", "-b", branch], cwd=work, extra_env=env).returncode != 0:
            return " ".join(tags + ["BRANCH_FAIL"])
        with open(os.path.join(work, ".onboard_check"), "w") as fh:
            fh.write(f"onboard check {login} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        git(["add", ".onboard_check"], cwd=work, extra_env=env)
        git(ident + ["commit", "-qm", "onboard verify (temp)"], cwd=work, extra_env=env)
        r = git(["push", "-q", "origin", "HEAD"], cwd=work, extra_env=env)
        if r.returncode != 0:
            tail = (r.stderr.strip().splitlines() or [""])[-1][:120]
            return " ".join(tags + ["PUSH_FAIL " + tail])
        tags.append("PUSH_OK")
        code, _ = api(base, admin_cred, "DELETE",
                      f"/api/v1/repos/{repo}/branches/{branch}")
        tags.append("DEL_OK" if code in (204, 200) else f"DEL_HTTP{code}")
        return " ".join(tags)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(adir, ignore_errors=True)


# -------------------------------------------------------------------- helpers

def gen_password(n=20):
    alphabet = string.ascii_letters + string.digits  # no @ : # space -> URL/env safe
    return "".join(secrets.choice(alphabet) for _ in range(n))


def upsert_creds(path, login, password, url):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kept = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            kept = [ln for ln in fh.read().splitlines()
                    if ln.strip() and ln.split("\t")[0] != login]
    kept.append(f"{login}\t{password}\t{url}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(kept) + "\n")
    os.chmod(path, 0o600)
    return os.stat(path).st_mode & 0o777


def place_env(path, login, password, base, repo):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    body = (
        "# a2a-bus credential, issued by the bus admin. Never commit this file.\n"
        f"A2A_GIT_USER={login}\n"
        f"A2A_GIT_PASS={password}\n"
        f"A2A_REPO_URL={base.rstrip('/')}/{repo}.git\n"
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(body)
    os.chmod(path, 0o600)
    st = os.stat(path)
    return f"{path} mode={oct(st.st_mode & 0o777)} uid={st.st_uid} size={st.st_size}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", required=True)
    ap.add_argument("--repo", default="anc/a2a-bus")
    ap.add_argument("--base", default="http://192.168.199.2:3000",
                    help="Gitea base URL reachable from this host")
    ap.add_argument("--admin", default="anc")
    ap.add_argument("--store", default="/opt/data/home/.git-credentials")
    ap.add_argument("--creds", default="/opt/data/secrets/a2a-bus-creds.txt")
    ap.add_argument("--place", default=None, help="also write a 600 env file here")
    ap.add_argument("--no-verify", action="store_true", help="skip the clone/push proof")
    args = ap.parse_args()

    admin = read_store(args.store, args.admin)
    print(f"admin={args.admin} passlen={len(admin[1])}")

    code, body = api(args.base, admin, "GET", f"/api/v1/users/{args.login}")
    if code == 200:
        password = None
        if os.path.exists(args.creds):
            with open(args.creds, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    p = ln.rstrip("\n").split("\t")
                    if len(p) >= 2 and p[0] == args.login:
                        password = p[1]
        if not password:
            raise SystemExit(f"{args.login} exists but no stored password; reset it via the API")
        print(f"create=exists user={args.login}")
    else:
        password = gen_password()
        payload = {"username": args.login, "email": f"{args.login}@a2a.local",
                   "password": password, "must_change_password": False, "send_notify": False}
        code, body = api(args.base, admin, "POST", "/api/v1/admin/users", payload)
        if code not in (201, 200):
            raise SystemExit(f"create failed HTTP {code}: {body[:300]}")
        print(f"create={code} user={args.login}")

    code, body = api(args.base, admin, "PUT",
                     f"/api/v1/repos/{args.repo}/collaborators/{args.login}",
                     {"permission": "write"})
    print(f"grant={code}" + ("" if code in (204, 200) else f" body={body[:200]}"))

    mode = upsert_creds(args.creds, args.login, password,
                        f"{args.base.rstrip('/')}/{args.repo}.git")
    print(f"creds={args.creds} mode={oct(mode)} passlen={len(password)}")

    if args.no_verify:
        print("verify=SKIPPED (a 204 grant is not access; verify before reporting)")
    else:
        print("verify=" + verify_write(args.base, args.repo, args.login, password, admin))

    if args.place:
        print("place=" + place_env(args.place, args.login, password, args.base, args.repo))


if __name__ == "__main__":
    sys.exit(main())
