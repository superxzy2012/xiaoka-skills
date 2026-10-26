# GitHub-hosted bus: deploy key onboarding (outbound-only node)

When the bus repo lives on GitHub, a node with no inbound reachability and no shared mount gets
a **repo-scoped deploy key**, not an account PAT: only the public key ever crosses the wire,
write is scoped to one repo, and revocation is one Delete click in the repo settings.

## 1. Locate before you generate

Search every secrets location (local `secrets/`, NAS `A2A/secrets/`, scratch, task receipts) for
the key by its **comment tag** (`<node>-a2a-bus`) and the **SHA256 fingerprint already promised to
the owner** before minting a new pair. The fingerprint the owner was quoted is the search key —
if the original private key sits on another host's secrets dir and you generate a second pair,
the fingerprint promised to the owner no longer matches the key that lands on the node, and two
live identities now exist for the same node.

## 2. Generate and store

```bash
ssh-keygen -t ed25519 -N "" -C "<node>-a2a-bus" -f <secrets>/<node>_a2a_deploy_key
chmod 600 <secrets>/<node>_a2a_deploy_key   # pub is 644 — it is public
```

Record the private-key path in a sibling `.path` file. Never echo the private key;
`ssh-keygen -lf` output (fingerprint) is the only identity that goes into receipts and chat.
Prove a fetched private key matches the registered public key without printing either:
`ssh-keygen -y -f <priv> | diff - <(cat <pub>.pub)` → PAIR_OK.

## 3. Register through the owner's logged-in browser (CDP)

With no GitHub admin API credentials, drive the repo Settings UI over CDP on the owner's
Chrome. Open the tab with `Target.createTarget` + `background:True` — never take focus.

- URL: `https://github.com/<owner>/<repo>/settings/keys/new`
- Fill `#public_key_title` and `#public_key_key` with the **native value setter + input/change
  events** (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(...)`) —
  these are framework-controlled fields; a direct `.value=` assignment looks filled but submits empty.
- Leave the `#read_only` checkbox **unchecked** for write access (it is a read-only toggle;
  unchecked = Read/write).
- Submit with `form.requestSubmit()`; success = redirect to `/settings/keys` where the listing
  shows the new key with **Read/write**. Take evidence with `Page.captureScreenshot` before and
  after, and verify by reading the listing page text, not the form echo.
- If the listing shows the key but a later test fails, re-check the fingerprint on the listing
  page against `ssh-keygen -lf` — visually OCR'd fingerprints can be misread; the local
  fingerprint is authoritative.

## 4. Verify auth without git

The node-side host may not have git installed (an appliance shell with only ssh/curl). The SSH
handshake alone proves the key and its scoping:

```bash
ssh -i <key> -p 443 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -T git@ssh.github.com
# → "Hi <owner>/<repo>! You've successfully authenticated, but GitHub does not provide shell access."
```

The repo name in the banner proves the key is scoped to that repo. Use port 443 deliberately:
outbound-only nodes are typically firewalled to 443, and `ssh.github.com:443` is GitHub's
supported alternative to port 22.

## 5. Handoff and acceptance

- The private key travels as a 600 file via the owner's relay to the node — never group, never
  bus, never git history. The receipt carries only the fingerprint.
- Node side: remote `ssh://git@ssh.github.com:443/<owner>/<repo>.git`, key at `~/.ssh/` with
  `IdentitiesOnly=yes`, push only `outbox/receipt_*_<node>.json` (never `git add -A`),
  `pull --rebase` before each push.
- Final acceptance = the node's real `receipt_PING_<node>.json` commit visible on main — the
  banner plus one listing page are transport proofs, not integration proofs.

## 6. Verify-and-register variant: the node generates the keypair itself

A stricter node will refuse to receive a private key at all (private key that entered any chat
log is treated as burned). The clean shape then inverts §2–3: **the node mints its own keypair,
keeps the private half on its own disk, and posts only the public key**. Registrar-side flow:

1. Recompute the fingerprint locally before trusting the posted key:
   `ssh-keygen -lf <posted.pub>` — a pasted key may be truncated or altered in transit; compare
   against the fingerprint the node self-reported, and refuse to register on mismatch.
2. Register it via the owner's `gh` CLI, which needs no browser session:
   `gh api -X POST repos/<owner>/<repo>/keys -f title="<node>-a2a (write)" -f key="$(cat <posted.pub>)" -F read_only=false`
   → expect `verified: true` in the response. **`read_only=false` is what grants write** —
   forgetting it silently lands a read-only key and the node's first push fails as `403`.
3. Check the pre-existing key list first (`gh api repos/<owner>/<repo>/keys`): if a supposedly
   burned key was never registered, there is nothing to revoke — say so instead of performing
   a delete ritual.
4. The node tests with `ssh -T -p 443 git@ssh.github.com` (§4); repo name in the banner proves
   scoping. Give the node the exact remote URL — repo slug errors read like auth failures (§1
   of the pitfalls in SKILL.md).

Registering by `gh` CLI instead of the browser UI (§3) is preferred whenever the owner's `gh`
has `admin:public_key`/repo access — it is scriptable, evidence comes from the API response
rather than OCR, and it skips the framework-controlled-input pitfalls entirely.

## 7. 托管平台云 agent 的额外四步

平台托管的 Ubuntu（Muse 这类）能走密钥路线，但出站通道由平台权限层控制，顺序不能颠倒：

1. **先让 owner 放行出站 SSH**。默认 Deny 时握手死在 KEX 阶段：
   `kex_exchange_identification: banner line 0: <平台>: Outbound SSH is turned` /
   `Connection closed by <代理IP> port 3128`。处置：平台设置 → Permissions →
   Direct network protocols → 把 `ssh` 由 Deny 改成 Ask。改密钥/换端口/换 slug 都无效。
2. **确认 ssh 的运行身份再落位密钥**。平台 shell 常以 root 跑，ssh 读 `/root/.ssh`，
   不是 `/home/<user>/.ssh`；落错位置会静默 fallback 到 22 端口 + 默认密钥，看着像「密钥没生效」。
   config 与私钥同放该目录，600。
3. **补 known_hosts**：`ssh-keyscan -p 443 ssh.github.com >> /root/.ssh/known_hosts`。
   漏了这步首连报 `host key verification failed`，容易被误判成 key 未被授权。
4. **只给分支，不给 main**。镜像仓的 `main` 每轮被 force 重建，节点推到 main 的回执会被冲掉；
   双向通道的形状见 SKILL.md「通道拓扑」一节。

验收时不要接受节点的自述「三步都跑通了」：取它自报的 commit sha，隔一个镜像周期在仓库侧核对
`outbox/receipt_*` 文件是否还在、内容是否就是它写的那份。
