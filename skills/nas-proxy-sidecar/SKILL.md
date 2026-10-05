---
name: nas-proxy-sidecar
description: Use when NAS mihomo 旁路由配置客户端代理或测速。
---

# NAS mihomo 旁路由（192.168.199.2）

## 部署事实（2026-10-05 验证，已双机场）

```
容器: mihomo      主实例, KTM 机场 + 规则分流, --network host
       7891 mixed / 7892 redir / 7893 tproxy / 1053 DNS / 9090 面板
       面板 http://192.168.199.2:9090/ui/  密钥 KTM-yRY3IxvtDP_R2dEf
       目录 /volume2/2-AI/mihomo/
容器: mihomo2     NCINK 机场（vless IEPL，25 节点）, --network host
       7894 mixed / 9091 面板 密钥 mihomo2-ktm-test
       目录 /volume2/2-AI/mihomo2/
容器: mihomo-cron 订阅自动更新, --network host, 挂载 docker.sock
       crontab 源: /volume2/2-AI/mihomo2/cron/root
```

**客户端只连 7891**，内部：主实例的 `代理选择` 组默认走 `NCINK出口`（http 到 7894），
即 NCINK 为主、KTM 备援。NCINK 快 10 倍（100 vs 10 Mbps）且延迟更低（23 vs 47 ms）。

v2rayA（面板 :3017）已被 mihomo 取代，配置备份在 `config.json.bak-20261005`。

## mihomo 双出口配置（四个坑）

### 坑 1：url-test 组不选延迟最低的

主用组用 `url-test` 时，NCINK 延迟 23ms < KTM 47ms，但它仍选 KTM。
**原因**：`自动选择` 是**子组**，url-test 对嵌套组的延迟探测行为异常。
**解法**：主用组用 `select`（手动置首，不自动判断），故障切换交给独立的 `fallback` 组。

### 坑 2：fixed 标记钉死选择

面板点过一次节点，mihomo 持久化到 `cache.db`，之后 url-test/fallback 全都改不动：

```
GET /proxies/代理选择  →  {"fixed":"自动选择", "now":"自动选择"}
```

**解法**：`rm /volume2/2-AI/mihomo/cache.db` 后重启。**改完 proxy-groups 顺序必做**。

### 坑 3：改 YAML 插错顶层键

用 `str.replace("proxy-groups:", ...)` 插 `proxies:` 段会插到 `proxy-providers` 块里，
报 `yaml: line 28: did not find expected key`。
**解法**：`proxies:` 是顶层键（缩进 0），容器列表项缩进 2。结构复杂的直接整段重写。

### 坑 4：挂载文件不能 docker cp

`docker cp x mihomo-cron:/etc/crontabs/root` → `device or resource busy`（已挂载）。
**解法**：crontab 存 NAS 目录再 `-v` 挂入；改 cron 要 `docker rm` 重建容器。

### 验证顺序

改完配置先验**出口 IP**（`ip-api.com`）再测速 —— 只看延迟会被 cache.db 的 fixed 骗过去。

```bash
curl -s -x http://127.0.0.1:7891 'http://ip-api.com/json/?fields=query,country,isp'
```

## 每日自动测速

```
05:45  /volume2/2-AI/mihomo/speed_ab.sh   → /volume2/2-AI/mihomo/speed.log
```

**关键设计**：`7891` 主端口默认走 NCINK，直接测它**测不出 KTM 真实速度**。
脚本必须临时把 `代理选择` 组切到 `自动选择`，测完恢复原值：

```bash
curl -X PUT http://127.0.0.1:9090/proxies/%E4%BB%A3%E7%90%86%E9%80%89%E6%8B%A9 \\
  -H "Authorization: Bearer KTM-yRY3IxvtDP_R2dEf" \\
  -H 'Content-Type: application/json' -d '{"name":"自动选择"}'
```

NCINK 用独立实例 7894 直测，不受切换影响。
实测输出：NCINK 54.5 Mbps / 0.127s，KTM 10.0 Mbps / 0.111s。

## NAS 磁盘排查（清错过地方）

```
Docker Root Dir: /volume2/@docker   ← 不在根分区
独立挂载点: /home(7.2T) /volume2(11T) /volume3(7.2T) /ugreen(3.9G)
根分区真实内容只有 ~7G
```

**`docker system prune` 回收 10.6GB 但根分区零变化** —— 先查 `docker info | grep "Docker Root Dir"` 再动手。

### du 权限被拒时用特权容器

```bash
sudo -n docker run --rm --privileged -v /:/host:ro alpine \\
  sh -c 'du -sh /host/root/.[a-z]* /host/usr/* /host/var/* 2>/dev/null | sort -rh | head'
```

⚠️ **必须排除独立挂载点**：只看顶层 `du` 会把 `/home 118.6G` 误当成根分区占用。

### 真凶通常是缓存目录

`/root/.cache/rclone/vfs` 11GB（VFS 缓存模式下载产生，5349 个文件，2.5 个月未动）。
容器 `rclone-sidecar` 已停 2 周 → 缓存是死的。

**保守策略：先移到 volume3 观察，不直接删**
```bash
mv /root/.cache/rclone /volume3/_cleanup_20261005/
```
确认无用后 BOSS 手动 `rm -rf`。

### 停止容器不擅自删

`docker ps -a --filter status=exited` 的容器要问 BOSS —— 部分是在用服务（emby/aria2/openlist）。
`docker rm <name>` 删容器不删数据，加 `-v` 才连卷一起删。

两个都是三重校验，任一失败即中止不动配置：拉取大小 → 节点数 ≥5 → 重启后面板 ≥5 且出墙 200。

NCINK 特殊处理：证书自签必须 `curl -k`；订阅服务器在墙外，优先走 7894 代理拉、失败回退直连。
KTM 订阅必须带 UA `clash-verge/v1.6.0`，否则 403。

```bash
# 手动触发
sudo -n docker exec mihomo-cron bash -c '/volume2/2-AI/mihomo2/update_sub.sh'
# 看日志
tail -5 /volume2/2-AI/mihomo2/update.log
```

## 核心规则：GitHub 必须豁免代理

实测（vscode 仓库 401MB, --depth 1）：

| 路径 | 速度 | 用时 |
|---|---|---|
| 直连 | **270 Mbps** | 12.5s |
| 走代理 | 60 Mbps | 55.9s |
| linux 元数据 2.1GB | 直连 214 Mbps | 代理 **rc=128 超时失败** |

**原因**：GitHub 不在 mihomo 的国内直连规则里，走代理等于用机场的 7-8 Mbps 带宽去下本该 2000M 直连的内容。
**例外**：小请求（api.github.com / raw.githubusercontent.com）代理更快 —— raw 直连 0.83s vs 代理 0.36s，因为降的是握手延迟不是带宽。所以是「大仓库豁免、小请求随默认」，而 git 只有 clone/pull 是大流量，统一豁免即可。

## git 配置（git 不认 https.proxy！）

git 只有 `http.proxy` 和 `http.<url>.proxy` 两个键。**`https.proxy` 是 curl/npm 的键，git 写了无效**。

```bash
P=http://192.168.199.2:7891
git config --global http.proxy "$P"
# GitHub 系列逐一豁免（空值=不走代理）
for h in github.com api.github.com codeload.github.com raw.githubusercontent.com \
         objects.githubusercontent.com gist.github.com githubusercontent.com; do
  git config --global "http.https://${h}/.proxy" ""
done
```

验证是否真豁免：`GIT_TRACE_CURL=1 git ls-remote <repo> 2>&1 | grep -oE "Connect to"` —— 出现代理 IP 说明走了代理，应为空。

npm/pip 也要配（它们认自己的 proxy 键）：
```bash
npm config set proxy "$P"; npm config set https-proxy "$P"
# venv 无 pip 模块时直接写 ~/.config/pip/pip.conf
```

## 测速方法论（四个坑都踩过）

1. **单线程测速一律低估**。同一条 2000M 宽带：
   - 1 并发 622 Mbps / 8 并发 1729 Mbps / 32 并发 **1936 Mbps**
   单线程数字只反映 TCP 窗口，不是链路能力。要报带宽必须多线程。

2. **测速源本身就是瓶颈，会得出错误结论**。
   德国 Hetzner 单机房测出 820 Mbps，差点误判「宽带没跑满」。换中科大源 (`mirrors.ustc.edu.cn/ubuntu-releases/24.04/*.iso`) 后同一宽带跑出 1936 Mbps。
   选源原则：国内源测国内带宽，跨境源只能测跨境链路；先单次 `curl -w '%{http_code}'` 确认源可用再上并发。

3. **并发写同一文件导致统计失真**。`for i in ...; do curl -w '%{size_download}' >> 同一文件 & done` 会出现 1103643191 Mbps 这种荒谬值（awk 读到不完整行）。每个并发必须写独立文件，最后 `du -cb` 汇总。

4. **Mbps 换算别错**：字节数 × 8 ÷ 秒 ÷ 1000 = Mbps（×1024 是 MiB/s）。之前多算一位，把 8.5 MB/s 报成 8500 Mbps。

5. **被自己设的 -m 超时掐掉**：`git clone` 配了 `-m 30` 导致 rc=128，看日志才发现 clone 其实在正常进行。测大仓库要耐心等，不设短超时。

## 机场限速判定

单线程 7-8 Mbps 且**六个不同国家节点高度一致**（7.0-8.6）→ 是套餐按流量限速，不是节点问题。
佐证：订阅显示剩余 489.82 GB / 17 天重置 ≈ 每天 28GB，与 7-8 Mbps 吻合。
真限速节点会有明显差异（香港 30ms vs 美国 200ms 带宽差）。要跑满宽带只能换套餐，配置层无解。

## ssh 到 NAS 的权限边界（重要）

```bash
ssh -o BatchMode=yes -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2
```

- 免密登录 ✅（2026-10-04 打通）
- `sudo -n` 只免密 `/usr/bin/docker`，其他命令要密码
- **写 /volume2 下非 obsidian_vault 的文件会被拒**（属主 root 或 1005）。绕法：
  `sudo -n docker run --rm -v <dir>:/d -v /tmp:/tmp:ro alpine sh -c 'cp /tmp/x /d/x'`
- `ping` 不可用（缺 cap_net_raw）
- 宿主 bridge0 实际 IP 曾是 192.168.199.242，不是 .2 —— 别硬编码，用 `ip -4 addr show bridge0`

## 容器间网络（踩过两次）

mihomo 用 `--network host`，其他容器用 bridge → **bridge 容器里 127.0.0.1 访问不到 host 网络服务**。
- 错误做法：猜 IP（default 网关是 docker0 的 172.17.0.1，bridge0 才在 192.168.199.x）
- 正确做法：**让需要访问的容器也用 `--network host`**

## 订阅更新

每天 05:30，`mihomo-cron` 容器跑 `update_sub.sh`。三重校验，任一失败即中止不动配置：
1. HTTP 200 且 > 50KB
2. 节点数 ≥ 5
3. 重启后面板加载 ≥ 5 **且** Google 走代理返回 200

```bash
# 手动触发
sudo -n docker exec mihomo-cron bash -c '/volume2/2-AI/mihomo/update_sub.sh'
# 看日志
tail -20 /volume2/2-AI/mihomo/update.log
```

token 存 `.sub_token`（600 权限），**绝不写进脚本或命令行**（会进 ps 和 shell history）。
拉订阅必须带 UA：`curl -A "clash-verge/v1.6.0"`，否则 403 `token is null`。

## alpine 容器里跑 bash 脚本

alpine 默认无 bash，`#!/bin/bash` 脚本会报 `not found`（误导性错误，真因是缺解释器）。
容器启动时 `apk add --no-cache bash curl docker-cli jq` 一次装齐。

## 磁盘

NAS `/` 只剩 3.3G（19G 已用 15G）。装新镜像前先 `df -h /`。