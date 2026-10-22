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

**蜂群内部 peer 直接 `--admin`。** `gitea admin user create --username <login> --email <login>@a2a.local --admin --must-change-password=false`：admin 自动对**所有**私有仓有读写，不必再逐个 `PUT …/collaborators` 授权，也不受 `allow_create_organization` 之类新用户默认值困扰。代价是它能看见全部仓库，所以**一个 peer 一个账号**（便于单独吊销、审计谁推了什么），不要多人共用一个号。给外部/半信任方仍走 §3 的 collaborator + §7 的 deploy key 最小授权路线。

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

### 历史分叉（镜像任务报失败）的收敛流程

症状：`fatal: Not a valid commit name <sha>` + `FAIL: 历史分叉 —— gitea(x) 不是 GitHub(y) 的祖先`。

**先分清两种假象：**

1. **本地没有对象 ≠ 分叉。** 只跑 `git ls-remote gitea refs/heads/main` 拿到 sha 就 `merge-base`，
   本地没有该 commit，git 直接报 `Not a valid commit name`，被误判成历史分叉。
   判前必须 `git fetch gitea "+refs/heads/main:refs/remotes/gitea/main"`。
2. **真分叉要用 `git cherry` 分类，不能按提交数直接覆盖。**
   `git cherry -v <github> <gitea>`：`-` = 内容已在上游（双写/重复提交，sha 不同），`+` = 真独有。
   只搬 `+` 的那些，否则会把别人的工作抹掉。

收敛步骤（实测，零冲突）：

```bash
# 1. 临时裸库收两边对象
mkdir probe && cd probe && git init --bare -q .
git fetch <gitea-url> 'refs/heads/*:refs/gt/*'
git fetch <github-url> 'refs/heads/main:refs/gh/main'
# 2. 分叉点 + 两边独有数
git merge-base refs/gt/main refs/gh/main
git rev-list --count refs/gh/main..refs/gt/main   # gitea 独有
git cherry -v refs/gh/main refs/gt/main          # - 重复 / + 真独有
# 3. 在工作树里把 + 的提交 cherry-pick 到 GitHub main 之上，push GitHub
# 4. 确认两边内容一致后，force 覆盖 Gitea（内容已保全，force 才安全）
git push --force-with-lease=refs/heads/main:<旧gitea_sha> <gitea-url> HEAD:refs/heads/main
# 5. 回源验证：fetch gitea main，rev-parse 应与 GitHub 相同，并 git show 抽查文件内容
```

**force push 前必须先证明 Gitea 侧零独有内容**：`git diff <gitea> <github>` 里不能有纯删除行
（`git diff … | grep '^-[^-]'` 为空），只有新增/替换才安全。

**无法用 pre-receive 闸门按账号拦推送**：NAS Gitea 上 `public_key` 全属 `owner_id=1`（`anc`），
`mac-jarvis-nas-tm` / `xiaoka-hermes-nas-mirror` / `jarvis-xf-cloud` / deploy key 混在一起，
pusher 名字都是 `anc`。**但可以按 key 拦** —— 见下一节。

### 用 pre-receive.d 按 SSH key 做只读镜像闸门（实测有效）

Gitea 在 hook 里注入的不只是 pusher 名，还有 key id：

```
GITEA_KEY_ID=2              # public_key.id，用户 key 推送时
GITEA_DEPLOY_KEY_ID=0       # deploy_key.id，deploy key 推送时非 0
GITEA_PUSHER_NAME=anc       # 账号名（同账号下分不出人，别用它）
GITEA_PUSHER_ID / GITEA_PUSHER_EMAIL / GITEA_REPO_NAME / GITEA_REPO_USER_NAME / GITEA_REPO_ID
```

`hooks/pre-receive.d/<name>` 里的脚本能读到**完整 stdin**（`old new ref` 逐行），所以能精准做到
「哪个 key 能改哪个分支」。落点（宿主机）：
`/home/DY/gitea/data/git/repositories/<owner>/<repo>.git/hooks/pre-receive.d/<name>`，`chmod +x`，
**无需重启容器**。传脚本用 base64 管道（`echo <b64> | base64 -d > f`），别用嵌套引号 heredoc。

最小闸门（只让镜像 key 写 main，deploy key 一律拒）：

```sh
#!/bin/sh
ALLOWED_KEY_IDS="2"          # 2 = xiaoka-hermes-nas-mirror
reject=0
while read -r old new ref; do
  case "$ref" in
    refs/heads/main|refs/heads/master)
      ok=0
      case "$GITEA_KEY_ID" in
        "") ok=0 ;;
        *) case " $ALLOWED_KEY_IDS " in *" $GITEA_KEY_ID "*) ok=1 ;; esac ;;
      esac
      [ "${GITEA_DEPLOY_KEY_ID:-0}" != "0" ] && ok=0
      if [ "$ok" != "1" ]; then
        echo "❌ 拒绝：main 是 GitHub 枢纽的只读镜像分支（你的 key_id=$GITEA_KEY_ID）" >&2
        echo "   请推 git@github.com:superxzy2012/obsidian-sync.git，规则见 A2A/GIT-推送规约.md" >&2
        reject=1
      fi ;;
  esac
done
exit $reject
```

验证拦截时**必须真推**：`git push --dry-run` 只走认证/权限协商，**不触发 pre-receive**（实测
白名单故意改错，dry-run 仍 RC=0）。真推被拒后立刻 `git ls-remote` 确认远端 sha 未变，再用白名单
key 真推一次证明放行，最后 `--force-with-lease=<旧sha>` 回滚探针提交。

**hook 里不要写 `/tmp`** —— Gitea 在容器内，`/tmp` 与宿主隔离，日志会“消失”。写 `/data/...`
（= 宿主 `/home/DY/gitea/data/...`）。

查 key 清单（决定白名单）：

```bash
sudo -n docker exec -u git gitea sqlite3 /data/gitea/gitea.db \
  "SELECT 'PK',id,owner_id,name FROM public_key UNION ALL SELECT 'DK',id,repo_id,name,CAST(mode AS TEXT) FROM deploy_key;"
```

`owner_id=0` 的 public_key 也能正常推送，别据此排除；以 `name` 认人。新增镜像/agent key 后只需把
id 加进 `ALLOWED_KEY_IDS`，不用改任何 agent 的配置。

### 防误删：只增快照 + 每日校验（**不要做双写**）

需求「两个库互为备份、一个删了另一个还在」**不能用双向写实现**：

- 正常删除也会被双写：删文件 → 推 GitHub → 推 Gitea，两边同时没了。
- 「保留多的那个」= 无人值守 force push，判错一次就静默丢一边的真实工作；
  「多」≠「对」（多出来可能是垃圾，少的那边可能是清理过的正确版）。
- N 个 agent × 2 个远端 = 2N 条写入路径，rebase 时机不同 → 分叉概率随 agent 数线性上升。
- 出网不对称：Gitea 内网可达、GitHub 需出网，双写必然一边成功一边失败 → 立刻分叉。

**正确解法：写入保持单一路径（GitHub 主库 → Gitea 只读镜像），另加只增快照。**

脚本 `/opt/data/scripts/obsidian_backup.sh`（cron `96206f3774fd`，每天 19:10 UTC = 北京 03:10，
排在镜像 02:30 之后）：

1. 备份裸库 `/opt/data/backup/obsidian-sync.git`（volume1，与 vault 的 volume2 **不同物理盘**），
   `git fetch` GitHub 全 refs（heads + tags），增量只传新对象。
2. 每天给 main 打 `daily/YYYY-MM-DD` tag，并把 tag 推到 Gitea。
   → GitHub 被 force push / 删库，Gitea 与备份库仍有可完整检出的历史点；
   tag 不受 main 闸门限制（钩子只拦 `refs/heads/main|master`），**tag 永不删除**。
3. 校验：GitHub main vs Gitea main 的 sha + 文件数，区分「Gitea 落后（镜像没跑）」/
   「Gitea 超前（有人直推）」/「历史分叉」；再与昨日 tag 比增删，单日删除 >20 个或 >5% 就 ⚠️ 告警。

找回：`git --git-dir=/opt/data/backup/obsidian-sync.git show daily/2026-10-22:<路径>`。

脚本坑：① `timeout` **不能执行 shell 函数**（`timeout 420 g fetch` 报 rc=127），必须写全
`timeout 420 git --git-dir="$BK" fetch`；② 取昨日 tag 要 `grep -vx "$TAG"`，否则同一天重跑时
PREV==TAG，对比逻辑失效；③ 告警已在正文用 ⚠️ 标出，**退出码必须 0**，否则 cron 把正常告警判为运行失败；
④ 同一天 main 会前进多次，tag 推 Gitea 必须加 `--force`，否则第二次报
`Updates were rejected because the tag already exists in the remote`。

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
- **「连不上 Gitea」十有八九是认证，不是网络——分层测，别接对方的结论。** 顺序：① 从**对端机器**测 TCP（`Test-NetConnection <host> -Port 3000` / `nc -z <host> 3000`），通就排除了网络；② 用对端要用的凭据真跑一次 `git clone`，判据是**报错原文**——`remote: Failed to authenticate user` / `fatal: Authentication failed` 是认证，`Connection timed out` 才是网络；③ 认证失败就查 `SELECT id,name,is_admin,is_active FROM user`。
  **凭据清单文件存在 ≠ 账号存在。** 一份 `a2a-bus-creds.txt` 里可以列着五个 peer 的账号名而库里只有 `anc` 一个（建号那轮把行写进了文件、建号本身失败，或实例被重建过）；文件里的密码无从验证，唯一真相是 `user` 表。遇到「peer 说连不上」先查表，别先改网络配置、别急着加路由。
  `gitea admin user list --admin` 可能直接 exit 1 且零输出——别据此判断「没有用户」，改查 sqlite。
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
