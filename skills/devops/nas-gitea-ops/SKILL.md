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
  Parsing that file: each line is `https://<login>:<urlencoded-pw>@<host>:<port>` — split on the
  **last** `@` first (`body.rpartition("@")`); the left part is `login:pw`, the right part is the
  host. Splitting on the first `:` (or treating the first field as the login) yields a
  "admin creds not found" that looks like a missing entry. The file holds several accounts for the
  same host, so match the login exactly (`u == "anc"`) rather than taking the first hit —
  `git credential fill` can hand you another agent's row and the admin route then answers 403.
- **API calls**: write a `curl -K` config file (mode 600) containing one line `user = "login:password"`,
  then `curl -K <file> ...`. **Never `curl -u "$U:$P"`** — passwords containing `@`, `:`, `#` or other
  shell/URL special chars get mangled and the call fails auth with no obvious error (HTTP 401/empty).
- **Basic Auth variant**: `Authorization: Basic <base64(login:password)>` works for admin-user routes
  (`/api/v1/admin/users`) — encode from the same 600 config, don't hand-build the string.
- **SSH**: use the `gitea-mirror` key. scp-like `git@host:port/path` syntax rejects `:port` — use the
  `ssh://` form or `GIT_SSH_COMMAND="ssh -p 2222"`.

## Admin path without the anc password (prefer this)

The NAS gitea container ships its own CLI and DB, so most admin work needs **no password at all** —
do not stall on "I don't have anc's password":

```bash
# 必须 -u git。以 root 跑会 FATAL mustNotRunAsRoot 并且什么都不创建（后续 sqlite 查询拿到空 id）。
sudo -n docker exec -u git gitea /usr/local/bin/gitea admin user create \
  --username <login> --password "$PW" --email <login>@a2a.local \
  --must-change-password=false --config /data/gitea/conf/app.ini
sudo -n docker exec -u git gitea sqlite3 /data/gitea/gitea.db \
  "SELECT id,name,is_admin,is_active,allow_create_organization FROM user WHERE lower_name='<login>';"
```

For anything the CLI has no subcommand for (collaborators, user SSH keys, repo settings), mint a
**throwaway admin token** instead of hunting the password:

```bash
TOK=$(gitea admin user generate-access-token --username anc --token-name "tmp-$(date +%s)" --raw \
      --config /data/gitea/conf/app.ini | tail -1)
curl -s -X PUT "http://localhost:3000/api/v1/repos/anc/<repo>/collaborators/<login>" \
  -H "Authorization: token $TOK" -H 'Content-Type: application/json' -d '{"permission":"write"}'
sqlite3 /data/gitea/gitea.db "DELETE FROM access_token WHERE name='tmp-...';"
```
Delete the token in the same script and state in the receipt that the table is back to only the
pre-existing `gitea-admin` row. A leftover token is an unaudited credential.

Pass generated passwords on **stdin**, never argv — `docker exec -e PW=…` and `sh -c "…$PW"` both
show up in `ps` on the host:

```bash
printf '%s\n' "$PW" | sudo -n docker exec -u git -i gitea sh /tmp/inner.sh   # inner.sh: read -r PW
```

Lock the account down to the minimum in the same pass (a fresh user defaults to
`allow_create_organization=1`):
`PATCH /api/v1/admin/users/<login>` → `{"allow_create_organization":false}`.

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
ls-remote and clone only prove READ. To prove WRITE, prefer `--dry-run` — it still runs
`receive-pack` server-side (so a missing write permission fails here) but lands nothing, so there is
no test branch to clean up:

```bash
TH=$(mktemp -d)
printf 'machine 192.168.199.2\nlogin <login>\npassword <pw>\n' > $TH/.netrc && chmod 600 $TH/.netrc
export HOME=$TH
cd /tmp && rm -rf probe && git clone -q http://192.168.199.2:3000/<owner>/<repo>.git probe
echo "CLONE_OK($(ls probe | wc -l))"        # read proof
cd probe && git checkout -q -b verify-<login>-$$
git push --dry-run origin HEAD              # write proof
```

Credentials go in a 600 `.netrc`, not in the clone URL — a password with `@ : #` breaks the URL and
the failure looks like a network error. Feed the password to a probe that runs inside a container
via stdin for the same reason. If you do fall back to a real temp-branch push, delete the branch
through the API and confirm only `main` remains (`GET /branches`).

This is the check that separates "the API said 204" from "the account can actually push" — run it
before telling a peer their credentials work.

### 6) Verify secrets are not tracked
`GET /api/v1/repos/<owner>/<repo>/git/trees/<branch>?recursive=true` → scan `tree[].path` for
`secret`/`cred`/`.env`. A `.gitignore` entry (`secrets/`) only blocks *untracked* files; `git add -f`
or `git add secrets/...` bypasses it and the value lands in history. Prefer keeping creds outside the
repo working tree entirely (a 600 file on the host / peer's local `~/.config`).

### 7) Deploy key — repo-scoped write for a peer you cannot hand a password to

Use this when the target has **no shared filesystem** and **no DM channel** (cloud node, other
owner's container). The only thing that crosses the wire is a *public* key, so it can travel over
the group chat safely — unlike a password. Scope is one repo, revocable independently.

```bash
# peer generates, sends the .pub line (public — safe to paste in group)
ssh-keygen -t ed25519 -C "<node>@cloud" -f ~/.ssh/id_ed25519_gitea -N ""

# you attach it (script takes the key on stdin, repo+title as argv)
printf '%s\n' "ssh-ed25519 AAAA... <node>@cloud" | \
  ssh DY@192.168.199.2 'sudo -n docker exec -u git -i gitea sh /tmp/add_deploy_key.sh anc/a2a-bus <node>-cloud'

# peer clones over SSH
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_gitea -o StrictHostKeyChecking=no -p 2222" \
  git clone ssh://git@100.66.1.7:2222/anc/a2a-bus.git
```

API underneath: `POST /api/v1/repos/<owner>/<repo>/keys` → `{"title":…,"key":…,"read_only":false}`,
201 on success. `read_only:false` lands as `deploy_key.mode=2` (**2 = Write**). `DELETE` the same path
with the **`deploy_key.id`** (not `key_id` — the table has both) → 204.

**Prove the channel before the peer exists.** Generate a throwaway keypair, attach it, run
`git ls-remote ssh://git@<host>:2222/<owner>/<repo>.git`, then delete it and assert
`SELECT count(*) FROM deploy_key` is back to its prior value. This converts "the API said 201" into
"a key of this shape can actually read the repo", and it costs one minute.

Also check `protected_branch` for the repo: no protected branch means the key can push `main`
directly, with no PR step to explain to the peer.

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

- **Read the live state before provisioning — a concurrent session may have already done it.**
  `GET /api/v1/users/<login>`, `GET /api/v1/repos/<owner>/<repo>/collaborators/<login>` (204 = the
  grant exists) and a look for `outbox/receipt_<TASK-ID>*` are three cheap reads that settle
  "does this still need doing". The same bus task is often handed to several agents at once, so a
  404 observed minutes ago does not mean 404 now — re-provisioning on a stale read overwrites a
  working password or creates a duplicate. Search session history for the task id too: another
  session of yours may hold the receipt.
- **`active:false` or a `<uid>+<login>@noreply.<host>` email in the user GET is not a failure.**
  Accounts created through the CLI/API report those while cloning and pushing perfectly; judge the
  account by the `push --dry-run` probe, not by those flags.
- **`gitea` CLI run as root is a silent no-op** — it aborts with `mustNotRunAsRoot()` before doing
  anything, and the follow-up `SELECT id … WHERE lower_name='x'` returns empty, which reads like
  "the user wasn't created" when the real cause is the wrong uid. Always `docker exec -u git`.
- **`Permission denied (publickey)` is almost never a missing grant.** Check the `public_key` and
  `deploy_key` tables for the peer's fingerprint first — a key that was never registered fails
  identically to a key that was registered without write scope. Registering a user key has no CLI
  subcommand: `POST /api/v1/user/keys` with a throwaway admin token (`read_only:false`).
- **`deploy_key` and `public_key` have different columns — introspect before you SELECT.**
  `deploy_key` is `id, key_id, repo_id, name, fingerprint, mode, created_unix, updated_unix`;
  `owner_id` / `read_only` belong to `public_key`. Guessing the schema throws
  `no such column: owner_id` mid-script, which under `set -e` aborts *after* the write has already
  landed. Run `PRAGMA table_info(<table>)` once instead of inferring column names from a sibling table.
- **A provisioning script that dies mid-way leaves live side effects.** The failed SELECT above left a
  registered deploy key behind, and the script printed nothing about it. End every provisioning run
  with an explicit end-state assertion (`count(*)` of the table back to baseline, token table back to
  only pre-existing rows) and re-run the cleanup loop if it fails — an aborted `set -e` chain looks
  identical to a clean run from the outside.
- **Probe reachability from the target's own network before designing the delivery path.**
  "The peer can't reach the NAS" is usually an assumption. From a cloud mesh node, `100.66.1.7`
  answered on 3000 / 2222 / 3022 and returned an SSH banner — which is what made the deploy-key route
  viable. Measure the port from the peer's side; do not inherit someone else's claim that it is closed.
- **`git push --dry-run` is the write proof** — it runs `receive-pack`, so permission failures still
  surface, and it leaves no branch behind. Reserve real temp-branch pushes for proving the pack lands.
- **The NAS host has no `git` binary** — run clone/push probes inside the gitea container (it has git
  and reaches `localhost:3000` / `192.168.199.2:3000`), or from a machine that does.
- **Verify a transferred script's size before running it.** A remote command that feeds `cat > file`
  from ssh stdin and then `&& docker cp`/`sh file` in the same invocation can execute a 0-byte file:
  it exits 0 and prints nothing, which is indistinguishable from success. `base64 -w0 | ssh … 'base64 -d > f; wc -c f'`
  then run.
- **Don't fight quoting through nested ssh.** Single quotes are eaten by the outer shell, so a
  `WHERE lower_name='x'` query arrives as `"x"` and sqlite errors with `no such column`. Put the
  query in a script file and run the file. The same trap eats a whole inner shell script:
  `ssh host 'sudo -n docker exec -i c sh -c "<script>"'` mangles `$f` and redirections
  (`ambiguous redirect`). Pipe the script on stdin instead —
  `ssh … 'sudo -n docker exec -i <container> sh -s'` with the script as the command's `input=` —
  and pass any secret as a base64 literal decoded inside (`echo <b64> | base64 -d >> $f`).
- **A 600 creds file owned by `root:1005` on the NAS cannot be appended by the host-side python
  user.** Write it through a container that mounts `/volume2/2-AI` (`owjdxb` runs as root), then
  `chmod 600` + `chown 1005:1005`, and assert `grep -c '^<login>='`, `stat -c %a` and the line count
  in the same command — a silently failed append is indistinguishable from a successful one from
  the outside, and the next peer to read the file gets a 401 you will misread as a wrong password.
- **Never `curl -u "$U:$P"` with a generated password** — special chars break it silently; use `curl -K`
  config (600). The failure mode is a 401/empty body that looks like a network hiccup.
- **Anonymous GET must return 404 after `private:true`** — a 200 means the repo is still world-readable;
  re-check the owner/path you patched.
- **An empty repo (`auto_init:false`) cannot be cloned** — peers get "repository is empty" until the
  first push lands; populate before announcing the clone URL.
- **ls-remote/clone prove READ, not WRITE** — `push --dry-run` (or a real temp-branch push) is the
  only write proof; a collaborator API 204 is not.
- **Don't deliver passwords in chat or group** — Feishu bot-to-bot DM is blocked (code 230013), and a
  ledger `open_id` borrowed from another app's view fails with `99992361 open_id cross app` (send a
  one-message probe before designing a delivery path around a DM). Store in a 600 file and hand the
  *path*, never the *value*, in group — or switch to a deploy key so no secret has to move at all.
  See `feishu-bot-group-mentions`.
- **Don't assume Gitea can pull a private GitHub repo** — token scope + egress decide it; have the side
  with source read access push to Gitea (direction: cloud → Gitea, not Gitea → GitHub).
- **`git push git@host:port/path` fails** — scp-like syntax has no `:port`; use `ssh://git@host:port/...`.

## Depth

- `scripts/provision_account.py` — create user + grant write + append to a 600 creds file, re-run safe
  (409 = exists). Run `python3 provision_account.py <login> <owner>/<repo>`. Password never printed.
- `scripts/add_deploy_key.sh` — attach a peer's public key as a repo Write deploy key; reads the key on
  stdin, takes `<owner>/<repo> <title>` as argv, mints and deletes its own admin token, asserts the
  table state at the end. Run it inside the gitea container via `docker exec -u git -i`.
- Peer repo onboarding — registering a peer's key and realigning an unrelated-history repo onto the
  bus: `references/peer-repo-onboarding.md`.
- Account/credential delivery over chat: `feishu-bot-group-mentions` (230013 bot-DM block + relay path).
- Bus envelope contract & secrets delivery: `a2a-file-bus`.
