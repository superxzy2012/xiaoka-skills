---
name: a2a-bus-onboarding
description: Use when onboarding an agent onto the A2A Git bus.
version: 1.0.0
license: MIT
author: Hermes (curator)
metadata:
  hermes:
    tags: [gitea, a2a, credentials, onboarding, swarm, nas]
    related_skills: [feishu-bot-group-mentions, nas-docker-deploy, agent-governance]
---

# Onboarding an agent onto the A2A bus

Provision a Gitea account on the shared bus repo, grant scoped write, prove it with a real push,
and deliver the secret without leaking it.

## When to Use

- A peer agent / new node needs `git pull`/`git push` on the shared bus repo (`anc/a2a-bus`).
- You are asked to "open an account", "give them a deploy key", "let them read the task books".
- You must hand a secret to another agent and cannot DM it (bots can't p2p — see
  `feishu-bot-group-mentions`).

One account per agent, never a shared token: revocation is per-node, and the credential file
tells you who has access. The deliverable is **not** "user created" — it is "that identity
really cloned and pushed, and the secret sits where the target can read it".

## Procedure

### 0.0 先钉住对方是哪台机器上的哪个实例（同名 ≠ 同实例）

给一个「名字」发凭据之前，先证明这个名字现在指向哪台机器。同一个 agent 名可能已经搬到新主机、换了平台
重装，旧实例停用后其 IP / 根路径 / 凭据 / 端口全部作废 —— 按旧记录推断，会把凭据投到一台已经没有这个
agent 的机器上。

- **身份从对方自己身上取，不从历史记录取**：读它宿主上的 `~/.hermes/.env` 里 `FEISHU_APP_ID`、
  `~/.hermes/profiles/` 列表、`systemctl --user status hermes-gateway`。app_id 才是「这台机器是谁」的指纹；
  主机名、组网 IP、以及「云端 Hermes」这类描述都不唯一。
- **一台机器上只有一个网关实例**：某台已知机器上只跑着一个 app_id，那它就不是另一个 agent 的宿主，
  不要在那台上继续翻 profile 找「另一个人的目录」。
- **在共享 agent 卡里写「身份沿革」**：`A2A/agents/<id>.md` 顶部固定一段 —— 新实例生效时间、旧实例已停用、
  「与 X 是不同机器/不同云，路径与凭据不可互套」。其他 agent 读的是这张卡，不是你的记忆。
- **投递顺序固定**：通道（SSH/组网）→ 对方自己的 A2A 根路径 → 600 凭据文件 → 对方本机真跑一次
  clone/push 验收。新实例的 A2A 根是它自己新建的，不要套用任何既有路径。

### 0. Get an admin identity that actually works

Admin credentials live in the git credential store, one URL per line
(`http://user:pass@host:3000`). **Match on the username, not on the host** — see pitfall 1.

```bash
U=anc
P=$(grep -oE "://${U}:[^@]+@192\.168\.199\.2:3000" /opt/data/home/.git-credentials \
    | head -1 | sed -E "s|.*${U}:([^@]+)@.*|\1|")
printf 'user = "%s:%s"\n' "$U" "$P" > .curlrc.tmp && chmod 600 .curlrc.tmp
curl -s -K .curlrc.tmp http://192.168.199.2:3000/api/v1/repos/anc/a2a-bus | head -c 200
```

`curl -K <600 file>` is mandatory — `-u "$U:$P"` breaks on passwords with shell-significant
characters and silently authenticates as nobody.

### 1. Create the account

```
POST /api/v1/admin/users
{"username":"<login>","email":"<login>@a2a.local",
 "password":"<20 random alnum>","must_change_password":false,"send_notify":false}
→ 201
```

`send_notify:false` because there is no mailbox; the password is delivered out of band.
Generate with `openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 20` — no `@ : #` and no
spaces, which keeps it safe in URLs, `.curlrc`, and env files alike.

### 2. Grant scoped write

```
PUT /api/v1/repos/anc/a2a-bus/collaborators/<login>  {"permission":"write"}
→ 204
```

204 means "grant recorded". It is not evidence the agent can push — do step 3.

### 3. Prove it with a real push, then clean up

Clone shallow, push a throwaway branch, delete the branch via API (`DELETE
/api/v1/repos/anc/a2a-bus/branches/<name>` → 204). Anything less leaves a write grant nobody
ever exercised.

`scripts/gitea_a2a_onboard.py --login <name>` does steps 0–4 in one run and prints
`create= grant= verify= creds=` lines. Pass `--place <path>` to also drop the env file (step 4).

### 4. Store the secret outside any repo working tree

- Canonical ledger: `/opt/data/secrets/a2a-bus-creds.txt`, mode **600**, one TSV line per agent
  (`login<TAB>password<TAB>url`). Never printed, never pasted into chat, never committed.
- Per-node handoff: a `600` env file so the target never handles the password by hand:

```sh
A2A_GIT_USER=<login>
A2A_GIT_PASS=<password>
A2A_REPO_URL=http://100.66.1.7:3000/anc/a2a-bus.git
A2A_REPO_URL_LAN=http://192.168.199.2:3000/anc/a2a-bus.git
```

Keep secrets **out of the repo directory entirely** (`~/.config/a2a/`, or the agent's own home).
`.gitignore` only hides untracked files; one `git add -f` puts a secret into history forever.

### 5. Put it where the target can actually read it

If the target runs as a container on this host, deliver through its mounted home:

1. Find the container: `docker inspect --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' <container>`.
   A Hermes-style agent mounts its home at `/opt/data`, so host `<home>/secrets/x.env` is
   `/opt/data/secrets/x.env` inside.
2. Confirm **which** agent it is before writing: env often has no `app_id`, but the home holds a
   persona file (`SOUL.md` / `memories/AGENT_SOUL.md`) whose self-description names the node.
   `grep -rlm1 '<节点名>' <home>/SOUL.md <home>/memories/*.md`.
   Known map on this NAS: `hermes` → `/volume2/hermes/data` (小卡), `hermes-ancgm` →
   `/volume2/hermes/ancgm-home` (贾维斯). Container names are not agent names — never infer the
   agent from the container name alone.
3. Write from your own container via the shared NAS mount (`/opt/nas/volume2/<home>/secrets/`).
   `write_file` refuses `/opt/nas/**` — use `python3` (it also lets you `chmod 600` in the same
   breath).
4. Verify readability **as the container user**, not as root:
   `docker exec <container> sh -c 'id -un; ls -l /opt/data/secrets/x.env; head -2 /opt/data/secrets/x.env'`.
   A file owned by the wrong uid with 600 is invisible to the agent it was written for.

### 6. Hand off, then write the receipt

- Delivery channel: bots cannot p2p (`230013`). Route per `feishu-bot-group-mentions` — human
  owner relays, or the env file above lands directly on the target.
- Receipt: `receipts/<topic>.md` committed to `main` of the bus, then re-read it through
  `GET /api/v1/repos/.../contents/<path>` (expect HTTP 200 + a byte size). Push can be rejected
  by the mirror's periodic double-push cycle — retry with `git pull --rebase` before concluding.
- State which onboarding route you chose when more than one was offered, and why the other was
deferred. **Route choice, in order:** (1) shared filesystem — drop a `600` env file where the target
  reads it; (2) **deploy key** — the target has no mount and no DM; (3) password over a human-relayed
  private channel — last resort. Pick (2) early when (1) is unavailable: only a *public* key has to
  cross the wire, it can be posted in the group without leaking anything, and it is revocable per
  repo without rotating an account password. See `nas-gitea-ops` §7 for the attach procedure.

## Pitfalls

1. **`git credential fill` returns the first entry matching the host, not the admin.** When many
   agents share one Gitea host, a host-keyed lookup hands back some other node's account and the
   API answers `403 "user should be the site admin"` — which reads like a broken password. Parse
   the store and match `://<admin>:` explicitly.
2. **The bus repo is private from the moment it is created.** It carries dispatch orders; a public
   default is a leak that someone else has to notice for you. `"private": true` in the create call,
   then confirm anonymous `GET /api/v1/repos/<owner>/<repo>` returns 404.
3. **A 204 on the collaborator call is not access.** Push a temp branch and delete it. The same
   rule applies to "deploy key added" — test `git ls-remote` with that key, not the API echo.
4. **Two sources of truth diverge silently.** A file mirror of the bus (post-receive hook into a
   shared directory) is a second copy that goes stale without announcing itself. Prefer per-agent
   accounts; if a mirror is required, make it one-way, read-only, and labelled "cache — Git wins".
5. **`HEAD` moves under you.** The bus is double-pushed on a timer, so a hash you read minutes ago
   is already stale. Re-run `git ls-remote` when verifying instead of comparing against an old value.
6. **Compound remote pipelines get blocked.** `base64 | ssh | docker cp | docker exec` chains trip
   the approval gate and can hang until blocked. One purpose per remote call, script files pushed
   separately. If a step is blocked, report it as unverified — never re-run a variant to "get the
   same result" and never narrate it as done.
7. **Never claim the container-side end-to-end test passed when only the host-side one did.**
   "Account pushes from NAS, file readable in container, git present" is three verified facts and
   one honest gap — say it that way.
8. **"The peer cannot reach the NAS" is a claim to measure, not inherit.** Before redesigning the
   delivery path around it, probe the port from the peer's own network (`nc -z <mesh-ip> 2222`, or
   read the SSH banner). A mesh route that answers on 2222/3000 changes the answer from "relay the
   password by hand" to "attach a deploy key and let them clone".
9. **A provisioning run that aborts mid-script leaves live state.** `set -e` stops at the first bad
   statement, after earlier writes have already committed — a half-attached key or an undeleted token
   looks exactly like a clean run from the outside. End the run by asserting the end state (row counts
   back to baseline) and re-running the cleanup if it does not match.
10. **同名 ≠ 同实例。** 一个 agent 从旧主机搬到新云端后，旧主机的 IP、A2A 根、凭据、端口全部作废；
    按旧记录推断会把凭据投到已经没有这个 agent 的机器上，对方只会回「我这里没这个目录」。先读对方宿主上的
    `FEISHU_APP_ID` 确认身份，再谈路径（见 §0.0）。

## Credential hygiene (non-negotiable)

- No secret in a command line, a script literal, a group message, or a repo file — not even a
  temporary probe script that you intend to delete.
- `600` on every file holding one; `chmod 600` immediately after writing, and re-`stat` to confirm.
- Read-only sharing of the ledger is fine; echoing any value into chat is not. Report lengths and
  paths, never content.

## Depth

- `scripts/gitea_a2a_onboard.py` — create + grant + verify + store (and optionally place) in one
  idempotent run; safe to re-run on an existing login.
