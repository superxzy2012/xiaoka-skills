# GitHub 传输通道判据（git 镜像 / peer 直连）

判通道时**按层分开测**，每层结论不能外推到下一层。四层：TCP → SSH 认证 → git 读（`ls-remote`）→ git 写（`push`）。

## 判据表

| 层 | 命令 | 正常 | 异常含义 |
|---|---|---|---|
| TCP 22 | `bash -c 'cat </dev/null >/dev/tcp/ssh.github.com/22'` | 通 | 多数网络**不通**；不要因此判「SSH 被墙」 |
| TCP 443 | 同上换 `/443` | 通 | 443 是 SSH 的备用口，通常通 |
| SSH 认证 | `ssh -p 443 -i <key> -T git@ssh.github.com` | `Hi <owner>/<repo>!` | `Permission denied` = 密钥没挂到仓，不是网络 |
| git 读 | `git ls-remote ssh://git@ssh.github.com:443/<o>/<r>.git` | 秒回 SHA | 挂 = 数据面问题（代理/隧道/MTU） |
| git 写 | 推一个一次性分支 | 成功 | 挂 = 同上，**且要区分是本地 git 还是通道** |
| HTTPS 直连 | `git ls-remote https://github.com/<o>/<r>` | — | 常见挂死；`api.github.com` 能通不代表它通 |
| HTTPS + 代理 | `-c http.https://github.com/.proxy=http://192.168.199.2:7891` | 可跑通 | 偶发 TLS `handshake failed`，只作回退 |

**核心陷阱：认证通 ≠ 写通。** `ssh -T` 是单发小包，反向隧道/代理都能扛；`git push` 是大流量长连接，同一路径常直接卡死。
反过来，`git push` 卡死也**不能**推出「SSH 被墙」——先单独测 `ssh -T`，通了就说明问题在数据面。

## NAS 侧：SSH over 443 + 按仓部署密钥（首选）

```bash
# 1. 生成镜像专用密钥（不要复用个人 key）
ssh-keygen -t ed25519 -N '' -C 'nas-mirror@<host>' -f /opt/data/.ssh/gh_mirror
chmod 600 /opt/data/.ssh/gh_mirror

# 2. 挂成该仓的写权限部署密钥（read_only=false 才是写）
gh api -X POST repos/<o>/<r>/keys \
  -f title='nas-mirror (write)' -f key="$(cat /opt/data/.ssh/gh_mirror.pub)" -F read_only=false

# 3. 认证层
ssh -p 443 -i /opt/data/.ssh/gh_mirror -o StrictHostKeyChecking=no -T git@ssh.github.com
```

镜像器里只留两个常量，不碰 token：

```python
GH_REMOTE = "ssh://git@ssh.github.com:443/<o>/<r>.git"
SSH_CMD = ("ssh -i /opt/data/.ssh/gh_mirror -p 443 "
           "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20")
subprocess.run(["git", "push", "origin", "HEAD:main"], env={"GIT_SSH_COMMAND": SSH_CMD}, timeout=120)
```

`git remote set-url origin ssh://git@ssh.github.com:443/<o>/<r>.git` 之后，`ls-remote` / `push` 都自动走 443，
不需要再传 `-c http.*.proxy`。

## 真推验收：一次性分支，验完就删

只看到 `push` 的 exit 0 不够（代理/过滤会把失败变成 0）。做法：

```bash
git checkout -B ping-test && git commit --allow-empty -m 'test: ssh push channel' \
  && git push origin ping-test
git push origin --delete ping-test   # 或 gh api -X DELETE repos/<o>/<r>/git/refs/heads/ping-test
```

推完用 `gh api repos/<o>/<r>/branches --jq '.[].name'` 确认分支**真的出现在远端**，再删。

## 幂等与补推

- 内容没变但上轮 push 失败过 → 必须先 `ls-remote` 取远端 HEAD，与本地 HEAD 比较后再决定推不推；
  只比「上次同步时间戳」会永久 `NOCHANGE`，远端停在旧版本。
- `ls-remote` 结果为空（网络抖动）时**不要**当成「远端为空需要强推」，`--force` 会抹掉别人的提交。
- 所有 git 调用带 `timeout=` 并捕获 `TimeoutExpired` 返回伪结果（`returncode=124`），否则 cron 整轮崩。

## peer 侧：反向隧道里的 git 数据面不可靠

`-R 127.0.0.1:2222:ssh.github.com:443` 这条隧道对 peer 来说只能保证**认证面**：

| 操作 | 结果 |
|---|---|
| `ssh -p 2222 -T git@127.0.0.1` | 通，`Hi <owner>/<repo>!` |
| `git ls-remote` / `git push` 走 `127.0.0.1:2222` | 常卡死，`git` 进程残留、日志停在表头 |

结论：**peer 的 GitHub 写操作不要走 SSH 隧道**（数据面必挂）；读走 HTTP 代理隧道，写走 HTTPS + 代理 + `credential.helper store`（见下两节）。Gitea 仍是 peer 的日常读写总线（隧道内网 HTTP，实测稳）。

### peer 侧读 GitHub：HTTP 代理隧道（已验证，首选）

SSH 隧道数据面不稳，但**把 NAS 的代理端口转过去**就稳：git 跑 HTTPS，代理隧道只搬 TCP 字节流，没有 SSH
信道多路复用的那套状态机。

```bash
# NAS 侧隧道脚本加一口（NAS_IP = 局域网地址，不要写 127.0.0.1）
-R "127.0.0.1:27891:${NAS_IP}:7891" \
```

```bat
:: peer 侧一次配好，之后 clone/pull 不再带参数
git remote set-url origin https://github.com/<o>/<r>.git
git config http.proxy http://127.0.0.1:27891
```

四步验收全过才算通：`curl -x http://127.0.0.1:27891 https://api.github.com/` → 200 →
`curl -x … https://github.com/` → 200 → `git ls-remote` 出 SHA → `git fetch` + `git pull --ff-only` exit 0
且 `git log --oneline -1` 与 NAS 侧远端 HEAD 一致。实测 `github.com` 首包 ~17s（代理 + 组网两跳），
慢不等于不通，别按 curl 超时判死。

**写：HTTPS + 代理隧道 + `credential.helper store`（已验证 `PUSH_EXIT=0`，远端分支真出现）。**
部署密钥只对 SSH 生效、SSH 数据面又不稳，所以 peer 的写权限只能靠 HTTPS token。落地配方：

```bat
:: 凭据文件用 SFTP 直写，绝不拼命令行/heredoc/脚本字面量
git config --global credential.helper "store --file=C:/A2A/.git-credentials"
git config --global http.https://github.com/.proxy http://127.0.0.1:27891
git config --global user.name  <peer>
git config --global user.email <peer>@mesh
```

- `icacls C:\A2A\.git-credentials /inheritance:r /grant:r Administrator:F SYSTEM:F` 收紧（Windows 无 mode bits，不收紧就是全机可读）。
- 提交身份固定成 peer 自己，否则所有推送都记在 owner 名下，事后分不清谁写的。
- 验收必须看两样：远端 `gh api repos/<o>/<r>/branches` 出现分支 + commit author 是 peer；只看 `PUSH_EXIT=0` 不够。
- peer 只推 `<peer>/*` 分支，不直推 `main`（`main` 由 NAS 镜像统一写）。
- **fine-grained PAT 无法用 API 创建**（只能网页点），别答应用户「我帮你造一个」；classic PAT 的 `public_repo` 就够推公开仓，接单前先 `gh api user --jq '.public_repos'` 报清爆破面与吊销代价。

### 重启隧道后的幽灵监听

`-R` 端口在 peer 上由 **sshd 子进程**持有。重启隧道时旧子进程不一定退出，仍 `LISTEN` 在那个端口：
新连接 TCP 握手成功、然后**零字节**——和「代理挂了」「密钥错了」表现一致，很容易白查一轮。

重启流程固定为：peer 侧按端口杀监听进程 → NAS 侧 `stop` → `start` → 回 peer 确认监听 PID 变了。
PowerShell：`Get-NetTCPConnection -LocalPort 27891 -State Listen -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`。

### 远端 Windows 上跑 git 的正确姿势

把 `ssh` / `git` 直接塞进远程 exec 通道（paramiko / `powershell -Command`）会挂：输出被整段缓冲，
进程又在等 stdin。可靠形态是**批处理 + 重定向 + 读日志**：

```bat
@echo off
set PATH=C:\A2A\git\cmd;%PATH%
set GIT_SSH_COMMAND=C:/Windows/System32/OpenSSH/ssh.exe -p 2222 -i C:/A2A/.ssh/gh_deploy -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL
cd /d C:\A2A\gh-mirror
del /q .git\index.lock 2>nul
echo === push %DATE% %TIME% === > C:\A2A\ghpush.log
git push origin HEAD:main >> C:\A2A\ghpush.log 2>&1 < NUL
echo EXITCODE=%ERRORLEVEL% >> C:\A2A\ghpush.log
```

由 `.ps1`（UTF-8 BOM）`Start-Process cmd.exe -ArgumentList '/c','C:\A2A\x.bat' -WindowStyle Hidden` 起，
`Start-Sleep` 后 `Get-Content <log> -Tail 8`。`.bat` 必须 ASCII + CRLF；`< NUL` 不能省（否则 git 等 stdin 挂死）。

**读日志先看字节数**：只有表头（~80–90 B）、没有 `EXITCODE` = 命令真卡在传输层，不是 harness 的问题。
`< NUL` 只能救「等 stdin」，救不了 SSH 隧道的数据面——同样的 bat 换成 `git -c http.proxy=… ls-remote https://…`
就能出结果。所以先换传输层（HTTPS + 代理），别在同一套 SSH 隧道参数上反复试。
