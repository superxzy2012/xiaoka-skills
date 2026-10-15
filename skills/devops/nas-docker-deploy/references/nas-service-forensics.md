# NAS 端口 / 服务归属取证

BOSS 甩来一个 `192.168.199.2:<port>` 或一张截图问「这是什么？要账号密码吗」时的标准流程。
原则：**先定位归属进程，再读它的配置，最后才回答** —— 不靠端口号猜，同一端口号在不同机器上完全可能是两回事。

## 0. 通道

```bash
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i /opt/data/.ssh/id_ed25519 -o ConnectTimeout=8 DY@192.168.199.2"
```

## 1. 先排除容器

```bash
$SSH 'sudo -n docker ps -a --format "{{.Names}}|{{.Image}}|{{.Ports}}|{{.Status}}" | grep :<PORT>'
```

命中 → 是容器应用，`docker inspect <name>` 看 env / mounts / labels。

⚠️ `{{.Ports}}` 里**既有镜像 `EXPOSE` 的端口也有实际绑定**（`3010/tcp, 0.0.0.0:30120->30120/tcp`），
`grep :<PORT>` 会因为那个 `EXPOSE` 端口误命中 —— 判归属以
`docker inspect --format '{{json .HostConfig.PortBindings}}'` 为准。

## 2. 没命中 → 宿主进程 / host 网络容器

```bash
$SSH 'for c in $(sudo -n docker ps --format "{{.Names}}"); do echo "$c -> $(sudo -n docker inspect $c --format "{{.HostConfig.NetworkMode}}")"; done'
```

非 `bridge` 的都值得看（自定义 bridge 名形如 `<stack>_<net>`，别只按 `-> bridge$` 过滤就以为「只剩 host」）。

### 2.1 端口 → socket inode → PID

端口先转十六进制（5005 = 0x138D、5006 = 0x138E、9090 = 0x2382）：

```bash
$SSH 'sudo -n docker run --rm --privileged --pid host --net host alpine sh -c "
  for f in /proc/net/tcp6 /proc/net/tcp; do awk \"\$2 ~ /:<HEX>\$/ {print \$2, \$10}\" \$f; done"'
# 输出形如： 00000000000000000000000000000000:138D 23662   ← 第二列是 inode
```

再反查持有该 inode 的进程：

```bash
$SSH 'sudo -n docker run --rm --privileged --pid host --net host alpine sh -c "
  for p in /proc/[0-9]*; do for fd in \$p/fd/*; do
    [ \"\$(readlink \$fd 2>/dev/null)\" = \"socket:[23662]\" ] && echo \"PID=\${p#/proc/} \$(tr \"\\0\" \" \" < \$p/cmdline)\"
  done; done"'
```

拿到 PID 后看它属于谁：

```bash
$SSH 'sudo -n docker run --rm --privileged --pid host alpine sh -c "cat /proc/<PID>/cgroup; ls -l /proc/<PID>/exe; tr \"\\0\" \"\\n\" < /proc/<PID>/environ"'
```

- `cgroup` = `/../<name>.service` → **宿主 systemd 服务**（NAS 自带功能多半是这种）。
- `cgroup` 里是容器 ID → `docker inspect` 那个容器。
- ⚠️ `netstat -tlnp` 在 `--net host` 的临时容器里**看不到 PID**（跨挂载命名空间），别指望它，用上面的 inode 反查。

## 3. 读宿主配置与日志（只读，不改）

```bash
$SSH 'sudo -n docker run --rm -v /:/host alpine sh -c "cat /host/etc/<svc>/<svc>.conf; tail -40 /host/var/ugreen/log/<svc>.log"'
```

绿联 NAS 自带服务的常见位置：

| 内容 | 路径 |
|---|---|
| 应用与 unit | `/ugreen/@appstore/com.ugreen.ctlmgr/<svc>/`、`/etc/systemd/system/<svc>.service` |
| 配置 | `/etc/<svc>/` |
| 日志 | `/var/ugreen/log/<svc>*.log` |
| 每用户数据 | `/var/lib/<svc>/<uid>/` |

## 4. 判「要不要账号密码」看配置，不看现象

浏览器弹认证框 ≠ 该服务本身要认证（也可能是反代或另一个服务）。以配置为准。已核实实例 —— **绿联内置 WebDAV（HTTP 5005 / HTTPS 5006，systemd `webdav.service`，二进制 `/usr/sbin/webdav`）**：

```ini
# /etc/webdav/webdav.conf
enable_http  = true   ; http_port  = 5005
enable_https = true   ; https_port = 5006
enable_anonymous = false                                   # ← 强制账号密码，不能匿名
cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem           # 自签 → 浏览器报「不是私密连接」
```

**它按 NAS 账号（uid）分根目录**：`/var/lib/webdav/<uid>/` 下每个软链 = 该账号能看到的一个共享目录，
据此可直接回答「用哪个账号登录、登进去能看到什么」：

| uid | NAS 账号 | 可见目录 |
|---|---|---|
| 1001 | `【BOSS英文名】` | `3-work`→/volume3/3-work、`SSD`→/volume1/SSD、`home`→/home/【BOSS英文名】、`music`→/volume2/music |
| 1002 | `WQ` | `3-work`、`SSD`、`home`→/home/WQ |

uid ↔ 账号名从 `/etc/passwd` 取（`awk -F: '$3>=1000 && $3<65000'`）；
**没出现在 `/var/lib/webdav/` 下的账号就是没开 WebDAV**，登了也没用。

**认证失败必须看日志分清两种**（含义完全不同，别混）：

```
Authentication failure / code: 1003, Incorrect account or password   → 用户名密码不对
No Authorization                                                    → 客户端根本没带凭据
```

## 5. 交付口径

报告里写清四件：**服务名 + 端口（含 https 备用口） + 认证要求 + 用哪个账号**。
账号名可以给（不是凭据），密码不猜、不问、不试 —— 让 BOSS 自己去 NAS「控制面板」改。
