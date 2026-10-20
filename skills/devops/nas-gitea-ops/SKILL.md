---
name: nas-gitea-ops
description: Use when provisioning NAS Gitea repos or accounts.
version: 1.0.0
license: MIT
author: Hermes (curator)
metadata:
  hermes:
    tags: [gitea, nas, a2a-bus, account-provisioning, repo-mirror]
    related_skills: [a2a-file-bus, feishu-bot-group-mentions, nodebabylink-mesh-troubleshoot]
---

# NAS Gitea operations: repo + account provisioning, privacy, access verification

Task class: stand up or modify the NAS Gitea server — create an empty repo (bus mirror),
provision per-agent accounts, grant write, make it private, or prove an account can actually
push. The instance is the a2a-bus backend and also a generic NAS git host.

## Instance & addressing

| access | URL |
|---|---|
| LAN (NAS subnet) | `http://192.168.199.2:3000` (HTTP API + web) |
| 组网 (NodeBabyLink) | `http://100.66.1.7:3000` — use this from cloud/remote peers |
| SSH push/pull | `ssh://git@192.168.199.2:2222/<owner>/<repo>.git` (key `/opt/data/.ssh/gitea-mirror`) |

Version ~1.27.x. API base `/api/v1`. The owner for bus repos is `anc`.

## Auth

- **Admin creds**: `git credential fill` with `protocol=http` `host=192.168.199.2:3000`, or parse
  `~/.git-credentials`. Never inline the password in a command.
- **API calls**: write a `curl -K` config file (mode 600) containing one line `user = "login:password"`,
  then `curl -K <file> ...`. **Never `curl -u "$U:$P"`** — passwords containing `@`, `:`, `#` or other
  shell/URL special chars get mangled and the call fails auth with no obvious error (HTTP 401/empty).
- **Basic Auth variant**: `Authorization: Basic <base64(login:password)>` works for admin-user routes
  (`/api/v1/admin/users`) — encode from the same 600 config, don't hand-build the string.
- **SSH**: use the `gitea-mirror` key. scp-like `git@host:port/path` syntax rejects `:port` — use the
  `ssh://` form or `GIT_SSH_COMMAND="ssh -p 2222"`.

## Procedure

### 1) Create repo (empty mirror)
`POST /api/v1/user/repos` → `{"name":"a2a-bus","private":<bool>,"auto_init":false,"default_branch":"main"}`.
For a bus mirror use `auto_init:false` (leave it empty; the pushing side populates it). Verify with
`GET /api/v1/repos/<owner>/<repo>` → check `full_name`, `empty:true`, `default_branch`. A repo with
`empty:true` cannot be cloned until the first push lands — populate before telling peers to clone.

### 2) Create account (per agent)
`POST /api/v1/admin/users` → `{"username":<login>,"email":"<login>@a2a.local","password":<20-char>,
"must_change_password":false,"send_notify":false,"source_id":0}`. 201 = created, 409 = already exists
(idempotent-safe, treat as success). Random password: `"".join(secrets.choice(string.ascii_letters+
string.digits) for _ in range(20))` — exclude `@ : #` and spaces so it survives in clone URLs.

### 3) Grant write
`PUT /api/v1/repos/<owner>/<repo>/collaborators/<login>` → `{"permission":"write"}` → 204.

### 4) Make private (bus carries 调度指令 — must be private)
`PATCH /api/v1/repos/<owner>/<repo>` → `{"private":true}`. Verify two ways: GET shows `private:true`,
**and** an anonymous (no-auth) `GET /api/v1/repos/<owner>/<repo>` returns 404. If it returns 200 the
repo is still public — the patch did not apply or was applied to the wrong owner.

### 5) Verify write access for a given account (do NOT trust ls-remote/clone)
ls-remote and clone only prove READ. To prove WRITE:
```bash
URL="http://<login>:<pw>@100.66.1.7:3000/<owner>/<repo>.git"
git clone --depth 1 "$URL" /tmp/probe && cd /tmp/probe
git checkout -b verify-<login>-<ts> && echo x > .verify && git add .verify && git commit -m verify
git push origin HEAD   # must succeed
# cleanup via API so the repo stays clean:
curl -K admin.cfg -X DELETE "http://192.168.199.2:3000/api/v1/repos/<owner>/<repo>/branches/verify-<login>-<ts>"
```
Confirm only `main` remains (`GET /branches`). This caught the difference between "API said 204" and
"the account can actually push" — run it before telling the peer their creds work.

### 6) Verify secrets are not tracked
`GET /api/v1/repos/<owner>/<repo>/git/trees/<branch>?recursive=true` → scan `tree[].path` for
`secret`/`cred`/`.env`. A `.gitignore` entry (`secrets/`) only blocks *untracked* files; `git add -f`
or `git add secrets/...` bypasses it and the value lands in history. Prefer keeping creds outside the
repo working tree entirely (a 600 file on the host / peer's local `~/.config`).

## Mirror a GitHub repo into Gitea
The pushing side needs READ access to the GitHub source with sufficient token scope. If your token
only has `public_repo`, a *private* source returns 404 — you cannot read it, so you cannot pull it.
Have the side that **can** read the source push to Gitea instead of expecting Gitea to pull GitHub:
```bash
git remote add gitea http://<login>:<pw>@100.66.1.7:3000/<owner>/<repo>.git
git push gitea main --all && git push gitea --tags
```
Then a `sync.sh` adds the Gitea remote as a second push target for ongoing dual-sync.

## Pitfalls

- **Never `curl -u "$U:$P"` with a generated password** — special chars break it silently; use `curl -K`
  config (600). The failure mode is a 401/empty body that looks like a network hiccup.
- **Anonymous GET must return 404 after `private:true`** — a 200 means the repo is still world-readable;
  re-check the owner/path you patched.
- **An empty repo (`auto_init:false`) cannot be cloned** — peers get "repository is empty" until the
  first push lands; populate before announcing the clone URL.
- **ls-remote/clone prove READ, not WRITE** — always do the temp-branch push+delete to verify a new
  account can actually contribute; the collaborator API returning 204 is not proof.
- **Don't deliver passwords in chat or group** — Feishu bot-to-bot DM is blocked (code 230013); relay
  via the human owner or expand the bot's availability scope. Store in a 600 file and hand the *path*,
  never the *value*, in group. See `feishu-bot-group-mentions`.
- **Don't assume Gitea can pull a private GitHub repo** — token scope + egress decide it; have the side
  with source read access push to Gitea (direction: cloud → Gitea, not Gitea → GitHub).
- **`git push git@host:port/path` fails** — scp-like syntax has no `:port`; use `ssh://git@host:port/...`.

## Depth

- `scripts/provision_account.py` — create user + grant write + append to a 600 creds file, re-run safe
  (409 = exists). Run `python3 provision_account.py <login> <owner>/<repo>`. Password never printed.
- Account/credential delivery over chat: `feishu-bot-group-mentions` (230013 bot-DM block + relay path).
- Bus envelope contract & secrets delivery: `a2a-file-bus`.
