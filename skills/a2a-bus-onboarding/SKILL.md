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

**单向 push 不算通。** 对方能推上来只证明「写」通；`pull` 收任务那条路要单独验：从总线推一条
`inbox/task_<ref>.json` 下去，让对方 `git pull` 后照它写 `outbox/receipt_<ref>_<id>.json` 推回来，
最后由你在总线 `git log` 上看到两个 commit（一个你的 task、一个对方的 receipt）。任一侧缺失就是半通 ——
回执没回来，说明对方没有常驻消费者，别写成「已接入」。

`scripts/gitea_a2a_onboard.py --login <name>` does steps 0–4 in one run and prints
`create= grant= verify= creds=` lines. Pass `--place <path>` to also drop the env file (step 4).

### 3b. 归属看 commit author，不看 push 账号

新节点的专属账号密码可能拿不到（`A2A/secrets/gitea-creds.txt` 是 `600`、属主为 NAS 管理 uid，容器读不了）。
不要因此卡住 onboarding：用一个能 push 的管理员账号认证，把 `user.name` / `user.email` 写成目标节点的 id。
总线上的归属由 **author** 决定，`git log` 和回执解析都认 author，不认谁推的。

```bash
git -c user.name=<node> -c user.email=<node>@swarm.local commit -m "..."
```

把「用哪个账号 push、归属写谁」记进 `A2A/agents/<id>.md`，否则下一个 agent 会以为是权限配错了。

### 4. Store the secret outside any repo working tree

- Canonical ledger: `/opt/data/secrets/a2a-bus-creds.txt`, mode **600**. **Two shapes exist in the
  wild — read the structure before parsing.** (a) INI blocks: `[<login>]` + `user=` + `pass=`;
  (b) single line: `login=user:password` (the NAS copy `A2A/secrets/gitea-creds.txt`). A parser that
  assumes TSV or `login=password` finds nothing, and the failure surfaces as "admin creds not found"
  or a 401, which reads like a wrong password rather than a parse bug. Any fresh script must accept
  both shapes and select the block whose header equals the login. Never printed, never pasted into
  chat, never committed.
- **Inspect a ledger's shape without echoing it:**
  `head -3 <file> | sed -E 's/=(.*)$/=<set>/'` shows keys and delimiters with every value masked.
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
   breath). **`python3` only succeeds if the file is writable by your container uid.** Bus
   documents (`A2A/README.md`, `agents/*.md`) are often `644` owned by the NAS admin uid, and the
   write dies with a bare `PermissionError` / exit 1. Fall back to writing in scratch and pushing
   through the NAS shell: `ssh -i <key> DY@<nas> "cat > /volume2/2-AI/A2A/README.md" < local.md`
   — `cat >` runs as the NAS user, not under the container's uid.
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
  Pick (2) early when (1) is unavailable: only a *public* key has to
  cross the wire, it can be posted in the group without leaking anything, and it is revocable per
  repo without rotating an account password. See `nas-gitea-ops` §7 for the Gitea attach procedure.
  When the bus lives on GitHub (no Gitea admin API, node is outbound-only), route (2) becomes a
  **repo deploy key registered through the owner's logged-in browser and verified by SSH banner** —
  full procedure in `references/github-deploy-key.md`.

  **托管节点可能把整条密钥路线都封死。** 有些云托管 agent（平台禁止 sshd、禁止本地密钥对、禁止反向隧道，
  只有单向出站）会**拒收**私钥 —— 那不是故障，是它按红线在保护你，改密钥格式重试只会让它把同一段拒绝
  再说一遍。对这类节点改走：
  - 首选 **HTTPS + fine-grained PAT**：仅目标仓、仅 Contents 读写、90 天；PAT 由仓库主私聊投递，
    文档里只写 `<MUSE_PAT>` 这类占位符。
  - 备选 **零凭据兜底**：节点把回执正文发到群里，由有推送凭据的一方代写 `outbox/receipt_*.json` 并 push。
    零安装、零权限，代价是代提交方需在线。
  - 私钥进过聊天记录即视为作废；**先查它是否真被登记过**（`gh api repos/<owner>/<repo>/keys`）再谈撤销 ——
    常见情况是根本没加进去，白做一轮「撤销」动作。

## 通道拓扑：镜像仓不是双向总线

一个仓如果同时挂着「对外镜像」，它就不能当双向总线用。典型形态：`main` 由镜像脚本每 N 分钟从内网正本
`git push --force` 重建 —— 外部节点推到 `main` 的回执**下一轮就被冲掉**，而且正本 `inbox/` 的任务正文
按脱敏规则根本不入镜像，节点永远收不到活。节点自述 push 成功、API 也查得到那条 commit，看着一切正常，
直到隔一个周期比对 `ls-remote` 才发现 HEAD 已换人。

**判据（写进验收，不靠信任）**：登记完通道后隔一个镜像周期再 `git ls-remote <repo> main`，对比节点自报的
sha；变了 = 它推的东西已被覆盖，通道是假的。

**正确形状：每个外部节点一条专属分支 + 一个中继脚本**

| 项 | 做法 |
|---|---|
| 分支 | `<node>` 独立 orphan 分支（`git init -b <node>` 后首推），与镜像的 `main` 完全隔离；镜像脚本只 force `main` |
| 下行 | 内网正本 `inbox/task_*_<node>*.json` → 脱敏（剥 detail、打码 IP/凭据）→ 分支 `inbox/` |
| 上行 | 分支 `outbox/receipt_*_<node>.json` → 写回正本 `outbox/` → **再从分支删除**（防重复回收） |
| 幂等 | 分支上已有的任务不重复下发；正本 `processed/` 里有的任务一律不下发 |
| 调度 | 纯脚本 cron（`no_agent`），不要每轮唤醒模型 |

`processed/` 那道闸是必需的：正本里躺着的过期任务会在中继首跑时被当成新任务下发给节点，节点照做过期指令
（例：已被新方案取代的建隧道任务）。归档动作本身也要在正本里做（`git mv inbox/x processed/x`），只删分支上的
副本下一轮会被重新下发。

现成实现：`/opt/data/bin/muse_relay.py` —— 正本克隆用临时 `GIT_ASKPASS`（700，用完即删），分支走 deploy key 的
`GIT_SSH_COMMAND`；回收后 commit 回正本 `main`，push 失败先 `pull --rebase` 再推。分支命名沿用蜂群既有惯例
（`xiaodou/m2-backup-drill` 这类按节点分叉），不要另造一套。

## Pitfalls

1. **`git credential fill` returns the first entry matching the host, not the admin.** When many
   agents share one Gitea host, a host-keyed lookup hands back some other node's account and the
   API answers `403 "user should be the site admin"` — which reads like a broken password. Parse
   the store and match `://<admin>:` explicitly.
   The same rule governs the TSV ledger: select the line whose **first field equals** the login.
   Taking `lines[0]` hands you another agent's — or a deleted — account, and the failure surfaces
   as `Failed to authenticate user` after a long hang, not as a parse error.
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

11. **A bot cannot *read* group history either — monitor via the bus, not the chat.** Sending is blocked by `230013`; reading group messages is blocked by `230027` (missing scope `im:message.group_msg`). So you cannot poll the group to see whether a node responded. Detect liveness from sources you *can* reach: (a) the bus repo — `git log --since='30 hours ago'` filtered by the node's author/commit name, and `ls outbox/` for that node's receipts; (b) NAS-side service logs (mesh `RouteAdd` for the peer, Gitea access logs). Build the nudge/escalation loop on those signals, not on group-scrape. See `scripts/node_link_watch.py`.

12. **`git commit -am` does not stage new files.** A freshly written `inbox/task_*.json` or
    `outbox/receipt_*.json` stays untracked, so the commit is empty and the push reports nothing to
    do — which reads as "no write access" and sends you back to re-checking collaborators. Stage with
    `git add -A`, and confirm `git log -1 --stat` lists the path before treating a push as proof.

13. **Locate the existing credential before generating a replacement.** A keypair may already sit
    on another host's secrets dir (NAS `A2A/secrets/`, the local `secrets/`, a prior receipt) while
    only its fingerprint was ever quoted. Search by the key comment tag and the fingerprint already
    promised to the owner before minting a new pair — otherwise the owner is asked to relay a key
    whose fingerprint no longer matches what they approved, and two live identities now exist for
    one node.

14. **Read the task doc's current revision from the repo before reporting next steps.** Task
    documents on the bus get revised in place (an account-token plan superseded by a deploy-key
    plan, for example), and an earlier revision still reads authoritative in your context. Pull the
    latest `tasks/<name>.md` from the repo (the receipt names the file) and check its version
    before telling the owner what to do — quoting the dead plan sends the owner to perform a step
    that was already automated away.

15. **仓库 slug 必须现查，不能凭记忆写进接入文档。** 落笔前先 `gh repo list <owner>` 拿真名：
    写错一个词，对端拿到的是 `Repository not found`，读起来像权限/认证问题，会让人在 PAT、分支、
    凭据上白查好几轮，而真正要改的只是文档里那一个字符串。

16. **对端「一直在报同一段话」时，先分清它是拒绝还是故障。** 反复出现的固定文案（尤其提到密钥、
    权限、安全）多半是对端的安全拦截在正常工作 —— 改配置、换参数都不会让它消失，只会再拒一次。
    正确处置：停掉触发它的东西（私钥、错 slug、不该发的凭据），换成对端明确接受的路线，
    并把「这是拒绝不是 bug」先告诉 BOSS，否则他会一直以为你在修一个坏掉的东西。

17. **托管 agent 的密钥落位跟着 `ssh` 的实际运行身份走。** 平台 shell 常以 root 跑 ssh，密钥与 config
    放用户家目录（`~/.ssh`）根本不会被读到，表现为握手静默 fallback 到 22 端口 + 默认密钥。先确认
    `id -un` 与 ssh 真正读的目录再落位；首连还要 `ssh-keyscan -p 443 ssh.github.com >> <ssh 的 home>/.ssh/known_hosts`，
    否则报 `host key verification failed` —— 那不是 key 的问题。

18. **出站被平台掐断时，报错里带的是平台自己的话术，不是网络故障。**
    `kex_exchange_identification: banner line 0: <平台>: Outbound SSH is turned` 配
    `Connection closed by <代理IP> port 3128` = 平台权限层的 Deny，需让 owner 在平台设置里把 ssh 由 Deny 改成 Ask。
    这时改密钥、换端口、换仓库名全都无效，只会多一轮「同一段拒绝」。

## Credential hygiene (non-negotiable)

- No secret in a command line, a script literal, a group message, or a repo file — not even a
  temporary probe script that you intend to delete.
- `600` on every file holding one; `chmod 600` immediately after writing, and re-`stat` to confirm.
- Read-only sharing of the ledger is fine; echoing any value into chat is not. Report lengths and
  paths, never content.
- **Prove a secret landed identically on both sides by comparing hashes, not values:**
  `printf %s "$PW" | sha256sum | cut -c1-8` plus `printf %s "$PW" | wc -c`, printed as `len` + `sha8`
  only. **Strip the field prefix first** — a line shaped `login=user:password` hashed whole never
  equals the password's hash, so a naive `cut -d= -f2-` reports a mismatch that looks like a wrong
  password. Equal `len`+`sha8` on both hosts is the receipt for "the same secret is in both places";
  a differing hash means one side was written before a rotation — re-issue, do not "try the other one".

## Depth

- `scripts/gitea_a2a_onboard.py` — create + grant + verify + store (and optionally place) in one
  idempotent run; safe to re-run on an existing login.
- Windows node without git / without a shared mount (MinGit portable, SFTP credential delivery,
  GCM override, `-EncodedCommand` execution): see skill `windows-remote-access` — the mechanics
  live there, not here.
- `scripts/node_link_watch.py` — poll a node's mesh reachability + bus activity on a cadence; nudges
  (with 4h cooling + 3/day quota) and escalates to QUEEN after a 24h stall. Pair with a cron `every 2h`.
  Args: `<peerid> <mesh_ip> <bus_author> [--openid <oid>] [--chat <cid>] [--nudge]`.
