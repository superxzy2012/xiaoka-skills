---
name: a2a-file-bus
description: Use when writing A2A task/receipt JSON to the shared bus.
version: 1.0.0
license: MIT
author: Hermes (curator)
metadata:
  hermes:
    tags: [a2a, multi-agent, file-bus, receipt, nas, handoff]
    related_skills: [feishu-bot-group-mentions, remote-host-admin-escalation, multi-agent-collaboration]
---

# A2A file bus: task envelopes in, receipt envelopes out

Task class: a peer agent (or the human) says "write a receipt / task / PING to the A2A bus" and
you must land a JSON envelope in the shared root that every host can see. The bus is a directory
contract, not an API: the file either exists with the right envelope and owner, or the peer's
poll never sees it.

## When to Use

- A peer asks for a PING / HEARTBEAT / DONE / BLOCKED receipt, or hands you a `task_*.json`.
- You need to address another agent by its standard id and leave proof on disk.
- Anything that ends with "回一句「A2A PING 已写」" — the message is the announcement, the file is
  the deliverable.

## Layout and standard ids

One authoritative root, several views of it:

| host | root |
|---|---|
| Mac (小米-codex, 小丽, 小丽2号) | `/Volumes/2-AI/A2A` |
| NAS host | `/volume2/2-AI/A2A` |
| Hermes / owjdxb container | `/opt/nas/volume2/2-AI/A2A` (or `/volume2/2-AI/A2A` if mounted there) |
| Windows (小七) | `C:\A2A` — written by 小七, bridged to NAS by a Mac-side sync job |

Subdirs: `inbox/` tasks (route by envelope `to`), `outbox/` receipts + heartbeats (route by
`from`), `processed/` (the receiver moves its own task here), `tasks/`, `results/`, `agents/`,
`archive/`, `secrets/` (never put credentials in an envelope).

Standard ids: `xiaomi-codex`, `xiaoqi`, `xiaoli`, `xiaoli2`, `xiaoka` (this agent, NAS), `jarvis`,
`azheng`, `friday`, `xiaodou`. Read `PROTOCOL.md` in the root before a non-trivial exchange — the
table above is the shape, that file is the contract.

**Agent names survive migrations; hosts do not.** The same id can be retired on one machine and
reborn on a brand-new VM (a cloud node taking over from a stopped local instance). Resolve identity
from the machine's own facts — `hostname`, whether its A2A root actually exists, its
`FEISHU_APP_ID` — and re-read the mesh route table before sending traffic anywhere. Two cloud nodes
are two independent machines: routing peer A's traffic at peer B's mesh IP gives "TCP connected,
zero bytes" rather than an error, so it reads like a broken tunnel instead of a wrong address.

## Procedure

1. **Read `PROTOCOL.md`** if the request is more than a PING — envelope field names and filename
   rules change, and peers parse strictly.
2. **Pick the directory by intent, not by convenience**: a receipt, heartbeat or PING goes to
   `outbox/`; only a *task for someone else* goes to `inbox/`. A receipt dropped in `inbox/` gets
   picked up as an unaddressed task by whoever polls first.
3. **Name the file** `receipt_<task_ref>_<your-id>_<YYYYMMDD_HHMMSS>.json` (tasks:
   `task_<task_ref>_<YYYYMMDD_HHMMSS>.json`). ASCII, digits, `-`, `_` only. On a collision add
   `_1`, `_2` — never overwrite someone else's receipt.
4. **Fill the envelope.** Receipt: `receipt_id`, `task_ref`, `from`, `to`, `ts`, `status`
   (`DONE`/`BLOCKED`/`HOLD`/`REJECT`/`PING`/`HEARTBEAT`/`IDLE`), `note`; `result_file` is
   mandatory for `DONE` and must actually exist. `ts` in `+08:00` — the fleet is on China time
   even when the container clock is UTC.
5. **Write atomically**: temp file in the same directory, then `os.replace`/`mv`. Peers poll on a
   timer; a half-written JSON is a `BLOCKED` receipt against you.
6. **Probe the write, then land past the uid boundary only if it fails.** Ownership is not stable
   across migrations/remounts: `outbox/` may be `1005:10 mode 755` (container uid 10000 gets
   `Permission denied`) or world-writable `666` after a share was re-mounted (direct write works).
   Always try one throwaway write first (`echo '{}' > outbox/.probe_$RANDOM.json` then `rm`) and
   read the result; do not reuse an old "container can't write" conclusion.
   Only if it is denied, escalate per `remote-host-admin-escalation` (its
   `hermes-container-boundary` reference): stage the bytes in the
   host's `/tmp` over ssh, then `sudo -n docker run --rm -v <host dir>:/o -v /tmp/stage:/p alpine
   sh -c "cp … && chown 1005:10 …"`. `scripts/a2a_write.py` does all of this — prefer it over
   hand-rolling.
7. **Verify by read-back**, not by the command's exit code: open the file through the container's
   mount path, `json.load` it, compare to what you meant to write, and check `ls -l` shows the
   parent directory's owner. Only then post the "已写" line.
8. **Report both halves separately.** "File landed and verified" is one fact; "peer acknowledged"
   is another and needs the peer's own reply. Never upgrade the first into the second.

## Pitfalls

- **A dispatched task with `first_response_minutes` gets a `PROGRESS` receipt before you start work.**
  Read the `task_*.json`, write `status: "PROGRESS"` with the step list, admin-access answer and an
  ETA, then do the work, then write `DONE`. The dispatcher measures silence from the task timestamp;
  four minutes of work with no PROGRESS still reads as a timeout, and a single late `DONE` cannot
  prove you were not stalled.
- **A receipt carries the path and permission bits, never the secret.** Record
  `path` / `format` / `mode` / `owner` / `size_bytes` and the granted `repo` + `permission`, so the
  peer can act on it, while the value stays in the 600 file. Also record what you *didn't* grant
  ("no admin, no org membership") — the negative is the part the peer cannot infer.
- **Permissions and mount paths change after a migration.** A conclusion like "uid 10000 cannot
  write outbox" is a snapshot, not a law — a remount can flip it to `666`. Re-probe with one
  throwaway write before escalating, or you burn a round on an escalation that is no longer needed.
- **Fresh receipts from any peer prove the whole bridge.** A receipt written minutes ago in
  `outbox/` (any `from`, not just yours) means git pull + push + rsync are all working; don't
  re-diagnose the relay because one peer is quiet — check that peer's own inbox/processed state.
- **`PUSH_OK` / `code:0` / exit 0 prove the code path, not the disk.** The only accepted proof is
  reading the file back through the mount. A container writing an unmounted host path succeeds
  into its writable layer and the file evaporates with `--rm`.
- **A file left owned by `root` is a new blocker.** chown it back to the parent directory's
  numeric owner in the same step, or the host-side sync bridge and the Mac apps cannot move it.
- **Do not move, edit or clean up other agents' files.** The receiver moves its own task to
  `processed/`; cleanup is the owner's or the coordinator's job. Touching a peer's file is how a
  bus loses trust.
- **Duplicate content, not duplicate names, is the real risk.** Re-running a write for the same
  `task_ref` should reuse the existing receipt if it already says the same thing; a second
  differently-timestamped receipt for one PING reads as two agents answering.
- **开工前先查回执：这个任务可能已经被并行会话做完了。** 同一份任务书会同时落到多个会话
  （人转发、调度器重派、另一个 profile），先 `grep -l <task_ref> outbox/` 再 `session_search(<task_ref>)`；
  已有 `status=DONE` 的回执就只补一句「已完成，回执见 X」，不要重做。重复执行会产出两份时间戳不同的回执，
  peer 无法判断哪份是真的。
- **被催「欠回执」时先回源核账，再决定写不写。** 调度方的记账可能停在它最后一次轮询那一刻：
  `git log --oneline -- outbox/receipt_<ref>_<id>.json` 查出它其实已经迟交过（实测迟到约 19h 仍被判 ESCALATED），
  再用 `gh api repos/<o>/<r>/contents/<path>?ref=main` 确认镜像也在。核账结果照实说三句：**在不在、迟到多久、
  当时为什么没收到**——把「它当时记账是对的」也讲明白，比争谁对更有用。重写一份新回执只会让同一条任务
  出现两个 DONE，而且把迟到这件事从账上抹掉了。
- **镜像器自己生成的文件也要过同一把脱敏尺。** `state/tasks_index.json` 这类索引是从任务卡正文抽字段
  拼出来的，会带出 tailnet IP；它不走「逐份 sanitize 源文件」那条路径，于是 leak-check 把自己生成的内容
  判成泄露、整轮中止（症状：cron 的 `last_error` 是 `LEAK_CHECK_FAILED: ... (ip)`，而源仓里根本没有那个文件）。
  修法：写盘前对拼好的字符串整体过 redactor；`127.0.0.1` 回环要豁免，否则带本地地址的任务卡会被判泄露。
- **Pushing a receipt into the bus *git* repo: `git pull --rebase` first, then prove it left the box.**
  Several writers share that repo (peers, mirror jobs, your own cron), so a plain `git push` after a
  long task routinely dies non-fast-forward — and piping the push through a truncating filter turns
  that into an exit 0 you read as success. Pull, push, then `git ls-remote origin main` and compare with
  local `HEAD`; also assert the file is in the remote tree (`git ls-tree --name-only origin/main
  outbox/ | grep <task_ref>`). 写进 NAS 共享目录 `/volume2/2-AI/A2A` 的文件**不等于**进了 Gitea 仓（宿主无 git、该目录不是工作树）；要入仓就在克隆里 `git add/commit/push`，再 `ls-remote` 比对。
- **交付物不可变：修订一律用新回执，不改历史字段。** 已 push 的回执/result 是别人核过的证据，改了就
  没法自证。要修正就写 `receipt_<ref>_<id>_<ts>_r2.json`，带 `revision` / `supersedes` /
  `prev_result_sha256_8` / `result_sha256_8` / `reason`，让新旧两版同时可核（旧 commit 的
  `git cat-file blob <旧sha>:<path>` 仍能取到原字节）。sha 变了要在回话里明说，别默默换值。
- **对端说「路径不存在 / 查不到」时，先分清它看的是正本还是镜像，再看它克隆够不够深。** 浅克隆里
  `git cat-file blob <sha>:<path>` 对超出深度的 commit 返回空——空返回是「这个 commit 不在我本地」，
  不是「这个路径不存在」。先 `--deepen` 再下结论；目录计数用 `git ls-tree -r <ref> --name-only |
  grep -c '^<dir>/'`（递归、指定 ref），`ls <dir> | wc -l` 是非递归，两者差一个数量级。
- **回执的 `result_file` 写相对仓根路径，并标注镜像可见性。** 正文目录（`results/` 这类）按脱敏规则
  不进公开镜像，只写 `results/x.md` 会让只有镜像读权的对端永远核不到；加一个
  `result_visible_in_mirror: false`，或把单份外发副本放进镜像白名单目录。
- **`to` must be the standard id**, not the display name, when the protocol table defines one —
  Chinese display names are accepted as aliases but ids are what scripts match on.
- **A missing `[Mentioned:]` head or empty `mentions` on the Feishu side is unrelated to the bus.**
  The chat announcement and the file are two independent channels; verify them independently.

## 消费方（轮询 worker）纪律

轮询型消费方（cron 每 N 分钟扫 `inbox/` → 分类 → 处理 → 写回执）有四条纪律，全是实测踩出来的：

- **先判归属，再花算力。** `inbox/` 里通常躺着别的 agent 的任务（`to=jarvis` / `xiaoka` / `xiaodou`）。任何「对每个任务调一次模型或分类器」的步骤之前，先做一次**无副作用**的归属判定（不带文本调 `parse_target(env, "")` 这类），把不是自己的原样留在原地。实测 16 个任务里 13 个不是自己的 → 每 3 分钟白烧 13 次模型调用，一小时 260 次。
- **多任务按紧急度重排，不按文件名或 mtime。** 用分类器给每个自属任务打 0–3 档，降序取前 `MAX_PER_RUN` 个；**只有一个任务时跳过打分**（省一次调用）。验收方式：故意让最不紧急的任务文件 mtime 最旧，看执行顺序是否被翻转。
- **空转必须是零外部调用。** 改完 worker 跑一次无任务场景计时（`--dry-run --quiet` 应 <1s）；还慢就说明有步骤在空 `inbox/` 上也调了外部服务。
- **模块级函数不能调用 `main()` 里嵌套的 `log()`。** 加进 worker 的新逻辑（分类器、闸门、重排）都在模块级，需要 `_jlog()` + 模块级 `QUIET` 开关，`main()` 里 `global QUIET` 赋值。普通运行看不出来，只有 `--dry-run` 走到那条分支才 `NameError` 崩掉。
- **并发轮次会抢同一个任务，move 必须容错。** cron 轮和手动轮可能同时 glob 到同一个 `task_*.json`，一方先 `shutil.move` 走，另一方 move 就抛 `FileNotFoundError` 把整轮 worker 打死（不是那一个任务失败，是这一轮后面所有任务都不处理）。`move_to_processed()` 要捕获 `FileNotFoundError` 并返回 `missing(已被其它轮移走)`，继续循环。锁文件挡不住这种窗口——锁只回答「有没有人在跑」，不回答「这条任务还在不在」。
- **回执 `note` 取尾部并剥掉思维链，不要 `[:400]`。** 模型输出的常见形态是「英文思考过程 + 中文答案」，甚至同一段里先英文后中文。取头部会把思考过程塞进回执、真答案被截掉，收件人看到的就是一屏 `Let me search…`。做法：先按 `Answer:` / `答案：` / `结论：` 的**最后一个**断点剥前缀，再丢掉不含中文的纯英文行，最后取尾部拼到限长；若清洗后中文字符 < 10（代码/英文交付物）就原样返回，别把正文删空。
- **清洗要作用在正文 `ans` 上，不能只洗回执 `note`。** 结果 MD、回执 `note`、验收输入三处读的是同一份 `ans`——把 `ans = _clean_answer(ans)` 放在 `ws_chat` 返回之后、`status` 判定与验收之前，三处一起干净。只洗 `note` 的话结果 MD 仍是半成品，验收还会把思维链算进交付质量。逐行清洗的具体规则（含结构行/缩进行的保护、汉字占比判据）见 `octop-ops` §6.5。
- **验收闸门先上观察模式，判但不拦。** 把 `{p, pass, why, mode}` 写进回执 `acceptance` 字段，`status` 仍只由调用成败决定；分类器不可达时返回 `degraded` 放行，验收环节绝不能成为主流程的单点故障。升硬拦的三个前置条件：攒够 100 个真实样本、人工抽查误判率 < 2%、打回能自动重投 `inbox/`——文件总线没有重试机制，打回就是任务凭空消失。

分类器接口本身（`state` / `questions` / `criteria` 形状、四种判断类型、降级表）见 `model-routing` 第九节；交付验收的样本矩阵、阈值与观察→硬拦的升级判据见 `references/delivery-acceptance.md`。

## 远程 peer 中继排障（云 VM / 星期五）

共享根「看不到某 peer 的动静」时，先分清是**网络**还是**它本地中继仓**。云 VM 这一跳已实测可从 NAS 直连：

```
ssh -i /opt/data/.ssh/id_ed25519 agentuser@100.66.1.6   # 节点小宝网段，VM-43-229-ubuntu
```

`100.66.1.6:22` 走 NodeBabyLink 隧道可达（`100.66.1.x` 上 ping 不通是正常的，relay 模式只转发 TCP）；
该 VM 上中继仓 `/home/agentuser/.a2a-bus`，工作区镜像 `/home/agentuser/A2A`，脚本 `~/A2A/sync.sh`，
日志 `~/A2A/sync.log`，cron `*/5 * * * * ~/A2A/sync.sh`。

**先确认「这个 peer 到底跑在哪台机器上」，再谈通道。** 判同机只看两样：`hostname` 和它的 A2A 根是否
真实存在（`ls -ld <root>`）。`~/.hermes/.env` 里的 `FEISHU_APP_ID` 是 bot 身份指纹，但同一台机器可以跑
多个 app，**app id 不同 ≠ 不同机**。agent 卡里写的「A2A 根 /home/xxx/A2A」只是自述，照它去开通道前先 ls，
否则会在别人的机器上白忙一轮。对端既不在组网里、也没有共享挂载时，缺的是 SSH/组网通道，不是文件权限。

**典型静默故障：`git pull --rebase` 被 rename/delete 冲突打死，sync.sh 在 pull 这步 `exit 1`，
于是「既不拉也不推」——任务进不来、回执出不去，但群里 @ 它照样秒回，极容易被误判成网络断了。**
冲突来源：本地 `dedupe.py` 把 `inbox/` 任务移进 `processed/`，而远端同一文件被删除。

修法（在 sync.sh 的 pull 处加兜底，本地真相在 `$ROOT`，rsync 会把没推上去的文件补回）：

```sh
if ! git pull --rebase --autostash --quiet; then
  git rebase --abort 2>/dev/null
  git fetch --quiet origin || exit 1
  git reset --hard origin/main --quiet || exit 1
fi
```

rsync 两端都加 `--exclude ".smbdelete*"`，否则 macOS/SMB 的临时删除文件会被当新文件提交。

**`git merge --ff-only` 在双向分叉时永久 skip，下游读到的是旧版本 —— 但本地文件看起来一直是新的。**
两边都在写时（本地领先 N 条、远端领先 M 条），ff-only 每轮都失败，日志只留一句 `merge-skip: not fast-forward`，
而本地 `group_feed.jsonl` 的 mtime 一直在动。于是「我这边文件是新的」成立，「peer 读到的文件是新的」不成立，
排障时极易判成对方出口坏了。

对端说「你的文件停在 X 点」时，**不要比本地 mtime，要比它读的那个 ref 上该文件的最后提交时间**：

```bash
git rev-list --left-right --count HEAD...gitea/main              # 401  20  ← 双向分叉，ff-only 必死
git log -1 --format=%ci gitea/main -- inbox/group_feed.jsonl     # peer 实际看到的时间点
git log -1 --format=%ci HEAD       -- inbox/group_feed.jsonl     # 本地真实时间点
```

两个时间点差多少，就是 peer 落后的量。修法是一次**非 ff 合并**（`git merge gitea/main`，冲突逐条取新）
或把脚本改成 `git pull --rebase`；只把本地文件重写一遍不解决任何问题。合并前先数远端独有提交，
别用 `reset --hard origin/main` 把 peer 的成果冲掉。

排障顺序（照抄即可）：`git status` 是否干净 → `ls .git/rebase-merge .git/rebase-apply .git/MERGE_HEAD`
→ 手动 `git pull --rebase` 看真实报错 → `git rev-list --left-right --count origin/main...HEAD`
→ 手动跑一次 `./sync.sh` → `git ls-remote origin main` 与本地 HEAD 比对（这才是「真推上去了」的证据）。

- **cron 里的 `git clone`（内网 Gitea）报 `could not determine hash algorithm` 或 404、而手工带凭据 ls-remote 却通 = 容器级 `http.proxy` 把内网请求劫进了 mihomo。** 全局代理对 `192.168.199.x` 一视同仁；修法是加主机豁免 `git config --global http.http://192.168.199.2:3000/.proxy ""`，别去改脚本。排障时要用 cron 的默认环境（不带任何显式凭据/代理参数）复现一次 clone 再下结论——手工带凭据测通不代表 cron 那条路通。
- **查定时任务故障先读 cron 的 executions.db 逐轮 status/error，再读脚本。** `enabled=true` 只说明排了期；任务可能已连续失败多轮而 GitHub 侧停更数小时，唯一早信号是最近一次镜像 commit 的时间戳变旧。
- **`~/.git-credentials` 条目按 host 字符串精确匹配，`:` 被编码成 `%3a` 与直写冒号是两个不同 key。** 排障前先打码列出全部条目并按 `user+host` 去重；凭据「存在」≠ helper 会选中它——最终判据是不带任何显式凭据的裸 `git clone/ls-remote` 能否成功。

**冻结窗口会摘 cron**：迁移冻结时 peer 会把 A2A 那条 cron 从 crontab 删掉（留下
`crontab.backup_<task_ref>.txt`），解冻后必须显式恢复，否则看起来「一切都对但就是不同步」。

**端到端验收**：任务里放 `nonce`，回执必须带同一个 nonce。只有「NAS 写任务 → peer 领走 →
回执带 nonce 回到 NAS 共享根」这条完整往返才算打通；单看 `git push` 成功或群里回了消息都不算。

**小豆身份已变更（2026-10-21 起）：旧 Mac 端小豆停用，现在是云端 Windows VPS 全新实例（`100.66.1.9`），与星期五 `.6` 是不同机器不同云。**
它本机的 A2A 根是 `C:\A2A\a2a-bus`（不是 `C:\A2A` 裸目录——裸目录是工具链/凭据暂存区，仓库要 clone 到 `a2a-bus` 子目录）；
无系统 git，用便携版 `C:\A2A\git\cmd\git.exe`（2.56.0），worker 已把该路径前置进 PATH。**不要**把 Mac/NAS 的路径假设套到它身上。

Windows 上的 agent 自报「连不上总线」时，先分开三件事：根目录、凭据、网络。

- **根目录是协议规定的 `C:\A2A`**，不是 agent 自己起的 `C:\Users\Administrator\<repo>` 之类。它按自选目录 clone 完，后续所有 peer 的路径假设都会错位。
- **凭据投 `C:\Users\Public\<name>-creds.txt`**：Public 对本机所有用户可读、写入不需提权。**不要**投到 agent 的私有 profile 目录——受限账号读别的用户的 `C:\Users\<name>\` 是拒绝访问（这是设计，不是故障）。写入走 base64 → PowerShell `[IO.File]::WriteAllBytes`，写完**回读三个字段**（`user` / `pass` / `clone_url`）确认，别只看 exit 0。
- **Windows 在 LAN 内就用 LAN 地址**（`192.168.199.2:3000`），组网 IP（`100.66.1.x`）在它那儿常常没有路由——但这是「可能」，不是结论：从它机器上实测两个地址的 3000 端口，再决定用哪个。
- **交付时说明 Public 是公共可读目录。** 内网可接受；要更严就改成一次性发完即删，或改用 deploy key（`nas-gitea-ops` §7）让密钥根本不落地。

## 凭据投递（secrets/，不走信封正文）

PROTOCOL 第 7 条：token/密码只放 `secrets/`，不进 task/receipt 正文。实操有三个坑：

- **`secrets/` 是 `755 1005:uucp`**，容器 uid 10000 写不了；NAS 宿主用户 `DY` 就是 uid 1005，能写。
  首选做法（单条命令、免 base64、属主一次设好）：本地先写文件，再用 stdin 灌进去，让挂着 `/volume2/2-AI` 的 root 容器代写：
  `ssh DY@192.168.199.2 "sudo -n /usr/bin/docker exec -i owjdxb sh -c 'cat > /volume2/2-AI/A2A/secrets/x.md && chmod 600 … && chown 1005:1005 …'" < local.md`
  （`owjdxb` 是 NodeBabyLink，挂 `/volume2/2-AI` 且以 root 跑）。**一条命令只干一件事**——别拼成
  `base64 | ssh | docker cp | docker exec` 长链，那条会被审批门拦死并浪费一轮。
  老办法（宿主用户不可用时）：`echo <b64> | base64 -d >`。容器侧路径是 `/opt/nas/volume2/…`，宿主侧是 `/volume2/…`，别混用。
- **云 peer 的 `~/A2A` 是 git 镜像，不是共享挂载**，`sync.sh` 只 rsync `inbox outbox tasks results agents processed`
  六个目录。所以写进 NAS 的 `secrets/` 它**永远收不到**；反过来把 token 塞进这六个目录就会进 git 历史。
  正确投递：直接写它本机 `~/A2A/secrets/`（`mkdir -p && chmod 700`，文件 600），这个目录不在 sync 清单里，只留在本机。
- **本机（NAS 容器）的 `~/A2A` 正相反：它是软链** → `/opt/nas/volume2/2-AI/A2A`，所以 `~/A2A/secrets/x` 与宿主
  `/volume2/2-AI/A2A/secrets/x` 是**同一个文件**，任务书里「落 ~/A2A/secrets 并同步到 NAS 工作目录」说的是一处。
  动手前 `ls -ld ~/A2A` 确认是软链还是本地目录，别把「同一个路径」当两步做，也别据云 peer 的经验假设它可写。
- 群聊里只报「路径 + 指纹（前 9 位…后 4 位）+ nonce」，token 原文不进群、不进信封。
- **凭据一旦出现在聊天里，当作已泄露：立即轮换 + 清掉所有落盘副本。** 轮换只是吊销旧的、重签新的；
  清副本才容易漏——抓页面回帖时存下的 `*reply*.txt`、试权限用的临时 clone 的 `.git/config`（token 在
  remote URL 里）都会静默带着明文。做法：先轮换，再 `grep -rl "<旧token>" /opt/data/cache /opt/data/secrets`
  并逐个删/改，最后再 grep 一次确认零命中；模板文件只留占位符，真值从 600 文件读进内存再发送。
  交付时直接告诉对方「建议你事后轮换」不如自己先轮换——它已经在日志里了。

**hive MCP 鉴权实况（2026-10-19 实测）**：`3456`/`3458` 的 `/mcp` **不校验 Bearer** —— 无 token、假 token、
真 token 都 200，`initialize` + `tools/list` 均通过（`tools/list` 各返回 1 个工具 `obsidian`）。
所以「开通 token」实际是签发一枚规范凭据供客户端占位、将来开校验直接可用；别把它说成安全边界。
云端必须用组网地址 `100.66.1.7:3456/3458`（`192.168.199.2` 从云端不可达）。

## Depth

- `scripts/a2a_write.py` — one-shot envelope writer: atomic write, uid-boundary escalation via the
  NAS host, collision suffix, read-back verification. Run it with `--dry-run` first to eyeball the
  envelope and target path; it prints `OK <path>` plus `owner=<uid>:<gid>` only after the read-back
  matches, and exits 1 on any mismatch.
- 交付验收（观察模式字段、样本矩阵、阈值校准、升级判据）：`references/delivery-acceptance.md`
- Permission/escalation detail: `remote-host-admin-escalation` →
  `references/hermes-container-boundary.md`.
- MCP token 签发（版式 / 指纹 / 回执 / 两句必说的实话）：`references/mcp-token-issuance.md`
- 远端 worker 接入（Windows peer 的脚本、幂等、验证方式）：见下 §已接入的远端 worker
- peer / 中继端口可达性分层判定（丢包 vs 被拒、对照组、双边抓包对账）：
  `references/peer-reachability-triage.md`
- GitHub 公开脱敏镜像（SSH over 443 判据表、部署密钥、代理回退、补推）：见下 §GitHub 公开镜像
  + `references/github-mirror-transport.md`
- Chat-side handshake (who to @, proving the mention landed): `feishu-bot-group-mentions`.

## 已接入的远端 worker（照抄即可）

| agent | 位置 | 触发 | 脚本 | 投递 |
|---|---|---|---|---|
| 小豆 | Windows `10_4_4_16`，组网 `100.66.1.9`，**全新云 VPS**（与旧 Mac 端无关，与星期五 `.6` 不同机） | NAS cron `fdaa4c3b5d57` 每 5 分钟经组网 SSH 跑 `C:\A2A\xd_worker.ps1` | `/opt/data/scripts/xd_a2a_worker.sh` | `a2a_dispatch.py --to xiaodou --cmd "..."` |
| winpc | 公司 Windows `DESKTOP-4PV5HTQ`，组网 `100.66.1.4` | **机器自己**的计划任务 `A2A-Worker-winpc`（`/ru SYSTEM`，每 5 分钟） | `C:\A2A\win_worker.ps1` | `a2a_dispatch.py --to winpc --cmd "..."` |

两种触发模式的选法：**能直连到机器且它常在线 → 用 NAS cron 推**（小豆，可集中改脚本、可观测）；**机器自己就在组网里且你不该把 NAS 变成调度单点 → 用机器本地计划任务**（winpc）。后者不在 NAS 侧留 cron，验收只能靠回执时间戳。

- worker 逻辑：`git pull --rebase --autostash` → 扫 `inbox/task_*.json` 取 `to=<自己>` → 已有 `outbox/receipt_<ref>_<id>.json` 就跳过（幂等）→ `detail.cmd` 用 `cmd /c` 执行 → 写回执 `status/note/detail.output`（截断 2000 字）→ commit+push（非快进则 `pull --rebase` 重试 3 次）。
- 模板：`windows-remote-access` 的 `templates/a2a_worker.ps1`（含幂等、重试、日志），改 `__AGENT_ID__` 即可用。
- `.ps1` 编码：**纯 ASCII 脚本不需要 BOM**（写 CRLF 即可）；**含中文才必须带 UTF-8 BOM**，否则 `powershell -File` 按 ANSI 解，中文变乱码。脚本里先把 `C:\A2A\git\cmd` 前置进 `$env:PATH`，否则任务里调不到 git。
- **计划任务以 SYSTEM 跑时，git 配置必须写在 `--system` 级**（`credential.helper` / `user.name` / `user.email` / `safe.directory`）——SYSTEM 的 `%USERPROFILE%` 是 `system32\config\systemprofile`，读不到交互用户的 global config；漏 `safe.directory` 直接 `dubious ownership` 拒跑。
- **机器本地计划任务的验收 = 手工 `schtasks /run` 一次 + 看日志 + 回 NAS 拉总线读回执正文**，三步都要。只看任务状态 `Running` 或只看日志里 `pushed:` 都不算——push 可能推到别的分支或回执字段缺失。
- 验证自动化是否真的在跑：投一条带 `echo <标记>` 的任务，**不要手工触发 worker**，等 5 分钟看回执时间戳。

## GitHub 公开镜像（脱敏只读镜像 + SSH over 443）

**传输优先级：SSH over 443 > HTTPS + 代理。** GitHub 的 **22 口不通**、`github.com` 的 HTTPS git 传输直连会挂，
但 **`ssh.github.com:443` 直连即通** —— 这是唯一稳定、且不需要把 token 拼进命令行的路。判据表与配方见
`references/github-mirror-transport.md`。

- 小豆（云 Windows）侧：**读写都走 HTTPS + HTTP 代理隧道**——NAS 侧 `-R 127.0.0.1:27891:<NAS_IP>:7891`，peer 侧
  `git config --global http.https://github.com/.proxy http://127.0.0.1:27891`。实测 `curl` 两个端点都 200、
  `git ls-remote` / `fetch` / `pull --ff-only` / **`git push` 全 exit 0**，远端分支真的出现、commit author 是 peer 自己的身份。
  SSH 隧道（`127.0.0.1:2222` → `ssh.github.com:443`）**只保证认证面**：`ssh -T` 秒回 `Hi <owner>/<repo>!`，
  但 `git` 数据面（`ls-remote`/`push`）会挂死、`git.exe` 常驻不退 —— 所以**写不要走 SSH，走 HTTPS + 代理**。
  认证面与数据面必须分开测：`ssh -T` 成功不代表写通道可用，`git push` 挂也不代表 SSH 被墙。
- **peer 侧的 HTTPS 写凭据只落 `.git-credentials`，且只能 SFTP 直写。**
  `credential.helper = store --file=C:/A2A/.git-credentials`，文件用 `icacls <file> /inheritance:r /grant:r Administrator:F SYSTEM:F` 收紧；
  传输走 SFTP 直写文件，token 绝不拼进命令行 / heredoc / `.bat` 字面量，脚本里只允许打印 `tok[:4] + "***"`。
  同时把 peer 的提交身份固定成它自己（`user.name=<peer>`、`user.email=<peer>@mesh`），否则所有推送都记在 owner 名下，事后分不清是谁写的。
- **classic PAT 的 `public_repo` 就够推公开仓**（够用且比 `repo` 窄）；fine-grained PAT **无法用 API 创建**，只能网页点，别答应用户「我帮你造一个」。
  接单前先报清爆破面：`gh api user --jq '.public_repos'` 拿到公开仓数量，并明说这把 token 能改删的是这几个仓、吊销会连带本机 `gh` 一起失效。
- **peer 写通道的验收 = 真推 + 立即清理。** `PUSH_EXIT=0` 只证明代码路径，不证明通道可用：推一个 `<peer>/ping`
  测试分支 → `gh api repos/<o>/<r>/commits/<sha> --jq '.commit.author'` 确认作者是 peer 自己的身份 →
  `gh api -X DELETE repos/<o>/<r>/git/refs/heads/<peer>/ping` 删远端 → peer 侧 `checkout main` + `branch -D`，
  最后 `git status` 干净才算完。少一步都会在真任务上翻车。
- **peer 只推自己的命名空间分支**（`<peer>/*`），不直推 `main` —— `main` 由 NAS 镜像统一写，两边同时写必然打架。
- **重启反向隧道后先清幽灵监听，再判断通道死活。** 旧 sshd 子进程仍 `LISTEN` 在被转发端口上时，新连接
  TCP 握手成功然后**零字节**——和「代理坏了 / 密钥错了」表现一模一样，白查一轮。固定流程：peer 侧按端口杀监听
  进程 → `stop` → `start` → 回 peer 确认监听 PID 已换。
- 同步器 `a2a_gh_mirror.py`：Gitea 私有完整总线 → GitHub 公开仓。范围 = `DOC_ALLOW` 文档 + `agents/*.md` + `state/tasks_index.json` + **`EXTRA_DIRS`（`outbox/` `state/` `receipts/`，仅 `.json/.md/.txt`，单文件 ≤256KB）**；逐份 sanitize（IPv4/密钥/token 正则打码），泄漏自检不过就中止。
- **镜像范围必须覆盖总线的证据目录，否则公开仓对审计毫无价值。** 回执在 `outbox/`、M0 审计副本在 `state/audits/`——只搬文档的白名单会让这些「明明写了却读不到」，而 peer 会当成同步停摆来派单。`results/`（带凭据路径的脚本 + 大 dump）、`processed/`、`inbox/` 正文按「公开仓不放正文」**有意排除**，理由写进 MIRROR.md，否则下一个接单者会当漏配再改一遍。
- 幂等靠「用 Gitea HEAD 的 `%cI` 当时间戳」，否则每轮都产生空 commit。
- commit message 带各段计数（`mirror: sync from gitea (17 docs, 8 tasks, 283 receipts/audits)`）——范围是否生效看标题即可判断，不必 diff 全树。
- **HTTPS 回退**（SSH 不可用时）：`api.github.com` 通、`github.com` 的 git 传输直连会挂，需显式走代理
  `-c http.https://github.com/.proxy=http://192.168.199.2:7891`。代理路线会偶发 TLS `handshake failed`、卡满超时，不要当主路。
- **每个仓挂自己的部署密钥**，镜像器用 `GIT_SSH_COMMAND` 指私钥：
  `gh api -X POST repos/<o>/<r>/keys -f title='nas-mirror (write)' -f key="$(cat x.pub)" -F read_only=false`，
  然后 `ssh://git@ssh.github.com:443/<o>/<r>.git` + `GIT_SSH_COMMAND="ssh -i <key> -p 443 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20"`。
  这样 token 不再出现在 argv / 进程参数 / 日志里，`ps` 拿不到凭据；写权限按仓授予，比全权限 PAT 收得紧。
- 内容没变但上轮 push 失败过 → 必须比较本地 HEAD 与 `ls-remote` 再补推；否则会一直 NOCHANGE 而远端停在旧版本。
- 所有 git 调用要带超时并捕获 `TimeoutExpired`（代理会 TLS handshake failed / 卡 120s），否则 cron 直接 exit 1。
- **cron 载体用 flock 串行，但 `timeout` 只杀包装层。** `timeout 200 sh wrapper.sh` 超时后 python 子进程可能残留并继续持锁，下一轮 `flock -n 9` 直接静默 exit 0——表现是「跑成功、没输出、内容没变」。排障顺序：`ps -eo pid,args | grep '[a]2a_gh_mirror'` 找残留 → 按 PID `kill -9`；**不要用 `pkill -f <pattern>`**，它会把这条 bash 命令行自身也匹配上，把自己 SIGTERM 掉（exit -15），看着像脚本被杀。
- **判定 cron 是否真成功看 job 的 `last_status` / `last_error`，不要只看脚本 stdout。** 修好之后、下一轮跑之前，job 里仍挂着上一轮的 error；反过来 stdout 静默也可能是 flock 让路而非成功。
- **「镜像 HEAD 卡住 >30min」先三分类，别直接重启进程。** 静态 HEAD 有三种成因：①**源仓空窗**——那段时间 Gitea 本来就没有提交，HEAD 不动是正常的；②**提交全在白名单外**——`state/audits`、`outbox` 单独提交，内容变了但镜像看不见，零 diff 自然不产生 commit；③真停摆。判定证据链固定两条：`cron/executions.db` 里该 job 逐轮的 `status`/`error`（有没有跑）+ 源仓 `git log --name-only` 逐笔比对改动路径是否落在镜像范围内（有没有东西可搬）。两条都正常就是 ①②，kill 进程、重装、改 cron 全是白工。
- **别顺着 peer 的诊断结论修。** 对方的 `diag_*.json` 可能把「白名单过滤」写成「sync job stopped」；照它重启只会浪费一轮。用上一条自己判，并在回执里**点名纠正**那句错误结论——否则错误根因会继续在群里传播，下一个人再按它修一遍。
### 双向化改造：去 force + rebase + 回捞 + inbox 入镜像（main 单通道）

公开镜像原本 `push --force` 重建 main，等于**把 peer 直推的东西下一轮抹掉**；同时不含 `inbox/`，peer 永远「没有任务」，回路是断的。四件必须一起改，缺一件就白改：

1. **去 force**：非 ff 时 `fetch origin` → 把本地镜像提交 `rebase origin/main` → 普通 push。冲突 `rebase --abort` + 告警 + 本轮不同步，**绝不 fallback 到 force**（宁可停一轮，也不静默覆盖 peer 的提交）。
2. **回捞（G2）**：fetch 后若 swarm 有 gitea 没有的提交（`outbox/receipt_*_muse.json` 这类 peer 独有产物），commit 回 gitea 正本；推不回就告警，别只 print 一句「N 个未回捞」当交差。
3. **inbox 入镜像（G4）**：把 `inbox` 加进 `EXTRA_DIRS`，否则 peer 侧看不到派单。验证看 commit message 的计数变化（`tasks=12 → 13`）。
4. **顺序（G3）**：先改镜像并实跑验证一轮，**再**让 peer 跑 push 测试；反过来测通也会被下一轮抹掉。

**rebase 必须带 identity，否则假冲突。** 脚本里 commit 用了 `-c user.name/-c user.email`，但 `git rebase` 自己也要建提交——镜像工作树没有 global identity 时 rebase 直接失败，被护栏当成「真冲突」abort，报出来的 ALERT_DIVERGE 是假阳性（手工带 identity rebase 一次就过）。定义 `REBASE = ["git","-c","user.name=…","-c","user.email=…","rebase"]`，**所有** rebase（含 `--abort`）都用它，别只改 push 那一处。

**双通道必然分叉，只留一条写路径。** 曾并行存在「main 镜像回路」与「独立 `muse` 分支 relay（每 5min 下发/回收）」两套设计，文档还互相声称对方不可用。裁决方式：以**真回执跑通的那条**为准（main：peer 提交 → 下一轮 ff 叠加未被冲 → gitea 回捞成功），另一条 cron `pause`、分支留作只读存档不删、文档里把作废理由写进原文（不删旧内容），否则下一个人照旧文档再搭一遍。

**给 peer 下单走 CDP 时**：attach 既有已登录标签（`Target.attachToTarget`），`Input.insertText` 填文本 + 点 `aria-label=发送`（按钮常常无文字、只有一个 svg，靠 `getBoundingClientRect` 定位到 textarea 右下方）；全程不 `createTarget`、不 `closeTarget`、不 `bringToFront`。发送成功判据 = textarea 值被清空，不是按钮 click 返回。回帖取证用「body.innerText 增长量 + 连续两轮长度稳定」判流式结束，再截图。

**attach 之后每条命令都必须带 `sessionId`，否则静默跑在浏览器层。** `Target.attachToTarget` 返回的
`sessionId` 要拼进后续**每一个** CDP 消息体（`{"id":n,"method":…,"params":…,"sessionId":sid}`）；
漏了就变成 browser-level 调用，`Runtime.evaluate` 返回空、`document.querySelector(...)` 读到 `None`——
表现是「页面没有这个元素」，而实际是**消息发错了会话**。自检方式：填完立刻读 textarea 长度，应等于
你插入的字符数；读到 `None` 就回头查 sessionId，不要改选择器。另外两个同族小坑：WebSocket 握手
`403 Rejected an incoming WebSocket connection from the http://127.0.0.1:<port> origin` 需要
`suppress_origin=True`（或直接连 `/json/version` 的 browser-level WS 再 attach）；
`json.load(urlopen(...).read())` 在 Python 3 会 `AttributeError: 'bytes' object has no attribute 'read'`，
必须先 `.decode()`。

**peer 可以拒收一份「它不是从自己的委托人那里拿到的」任务书，这是正确行为。** 它停下来问「请你用
自己的话告诉我做什么、做到哪一步」时，**不要重发同一份文件、也不要用「这份单已经落库了」施压**——
换一封自己写的指令，自带范围与边界（「只跑只读探测；不用 token；不建隧道；不写仓库；把原始输出贴回」），
并在里面明确不需要它信任任何文件。发指令与它实际执行是两件事：它拒绝那一次不代表通道坏，只代表
**授权链路没走它认的那条**。

**要两个视角对账时，要求对端自己打时间戳。** 让另一个观察方（抓包/日志）按秒对齐时，指令里必须写死
`date '+%Y-%m-%d %H:%M:%S %z'` 并在**每条探测前**各打一次；只让对端贴结果，两边永远对不上，等于白测。

**托管沙箱（muse.ai 这类云电脑）里 `succeeded` 不等于通：先看解析出的 IP。** 实测它的 MagicDNS 被沙箱
出口代理劫持，`nc -vz friday-bridge.tail95c8b3.ts.net 443` 返回 `succeeded!` 但括号里是
`(198.18.199.94)` —— 198.18.0.0/15 是 RFC2544 保留段，代理专用假地址，包根本没离开沙箱；同一时刻直连
tailnet IP `nc 100.119.150.22 443` 是 `Operation not permitted`（沙箱禁直连）。它自己贴的系统说明写得很清楚：
`Ordinary networking does not reach the tailnet … Reuse the runtime HTTP proxy, changing only its port to 3130`、
`Other TCP clients, including SSH, must use the same HTTP proxy with CONNECT support`、
`direct curl/SSH, ping, ICMP, and UDP do not test this path`。
⇒ 三条硬判据：① 解析 IP 落在 198.18/15 或 198.19 就是代理劫持，不是对端；② 对照组也「通」正是劫持特征
（真实链路不会连对照靶都成功）；③ 真通道只能走 runtime HTTP proxy + CONNECT（SSH 用
`-o ProxyCommand='nc -X connect -x <proxy>:3130 %h %p'`），且首次 CONNECT 到某地址需用户在对端权限页批准一次，
批准期间不要重试。

**对端自述「原始输出原样如下」而正文是空的，是常见形态，不是偶发。** 同一会话里它能连续两次这么写、
只留一句「443 和 22 都是通的」，一个 `rc=`、一行时间戳都没有。处置：不要跟它争，直接把要求写死
（「把终端里真实出现的文字整段复制过来，包括 succeeded / refused / timed out / rc= 的数字，不要总结」），
它下一次就会贴。判定「有原文」的方法是自己抓页面全文再 grep 关键串（`succeeded`、`rc=`、
`2026-` 时间戳行），而不是读它那段总结——自述与正文必须分开验。

**Gitea 1.27.3 的 token API 静默忽略 `expires_at`。** POST 建 token 时带上该字段返回 201，但响应体里
**没有** `expires_at`（不是写错格式，是被忽略），所以签不出真正的过期 token。补偿方案 = cron 硬吊销 +
到期前 7 天提醒，两条验收缺一不算完：① 建好后手动跑一次 `--dry`，确认能列出**目标 token 名**（别到
到期日跑了个空）；② 真删后拿该 token 明文回打 API，必须返回 `401 invalid username, password or token`，
把原始响应贴给对账方。吊销脚本要幂等（目标不存在返回 0），删前删后各列一次 token 列表。
**溯源上限**：Gitea 默认 access log **不记 User-Agent**（`app.ini` 只有 `LOG_SQL`），历史请求无法回溯 UA；
容器内来源 IP 经 docker 网关 NAT 后全是 `172.22.0.1`（自己发请求对照同样如此），审计 API 在 1.27 默认关闭
（`/api/v1/admin/audit-logs`、web `/admin/audit-logs` 全 404）。到这一步就如实说「查到日志极限」，
不要用「大概是某个人」填空——但行为链本身仍是证据：`PUT collaborator 422`（先授权发现没号）→ `POST 201`
（建号）→ `PUT 204`（再授权）→ `GET permission 200`（自查），这种带重试和事后校验的顺序说明是**脚本**，
不是人手动。

**归档/队列清扫必须三计数分列：命中 N / 实际 move M / 去重删除 D。** 「outbox 有回执或 processed 已有同名」只代表命中；其中 processed 已存在、inbox 那份只是重复的，只删 inbox 不 move（git name-status 里是纯 D，没有 A）。把三者混成一个「归档 N」会和对账侧的 `git diff --name-status`（D/A 对数）长期差 1——对方按文件系统 move 数核，你报的是命中数。日志要能直接对上 D/A 对数：move=D+A 成对、dedup=纯 D。

**短文件加字段会让 git rename 相似度暴跌，R055 不是正文丢失。** 422B 的 JSON 加上 status/archived_at/obsolete 等字段变 701B，rename 检测相似度可能只到 55%（R055），看着像「丢了一半」。核正文是否完整要逐字段 diff，别拿 rename 相似度当完整性判据。

**脚本解析 git 文件名必须先关 quotepath。** git 默认 `core.quotepath=true`，非 ASCII（中文）文件名在 `ls-tree/diff --name-only` 里被转义成带引号的八进制串（`receipt_A2A-PING_friday_"\346\226\260hermes_…json"`），后续按正则/白名单解析会失配——尤其「远端独有提交是否都是 muse 回执」这类全量文件名判断，一个中文 friday 回执就会被误判为非白名单 → return 6 假告警。统一在封装的 sh() 里给所有 `git` 子命令前置 `-c core.quotepath=false`（多个 -c 可叠加，与 user.name 共存）。**位置铁律：`-c` 必须在子命令之前**——`git -c core.quotepath=false ls-tree …` 对；`git ls-tree -c core.quotepath=false …` 报 `error: unknown switch 'c'`（-c 是全局选项，不是 ls-tree 的开关）。程序化注入时插到 `cmd[1:]` 之前，别 append。

**跨节点对账文件数先约定同一条命令。** `len(copied)`（本轮拷了几个）、`git ls-tree -r`（镜像树总数）、各业务目录分项求和是三个不同的数，两边各报各的永远对不齐，时间差还会再叠误差。固定一把尺：`git ls-tree -r <ref> --name-only | wc -l`（镜像树文件总数，含顶层文档），双方日志都打它。

- **改完镜像范围，验证要在 GitHub 侧做，不在推送侧。** `PUSHED files=N` 只证明本地算出了东西：`gh api repos/<o>/<r>/git/trees/main?recursive=1 --jq '[.tree[]|select(.type=="blob")]|length'` 对总数，`gh api repos/<o>/<r>/contents/<新路径>` 解 base64 看正文首行，再抽查新增目录的 `.[].name`。最后把「修复回执」本身写进 `outbox/`——它会被下一轮镜像带走，等于用新范围自证。
