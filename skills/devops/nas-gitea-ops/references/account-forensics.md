# 账号溯源：谁建的这个 Gitea 账号

适用：发现一个来源不明、或时间对不上的服务账号，需要回答「谁建的、能不能追」。
结论先给：**日志层基本查不到人，但能查到行为类型**。不要为了找一个 IP 无限深挖，也不要因为没有 IP 就不下结论。

## 四个查不到（先认清，省一轮）

| 想知道的 | 实际情况 |
|---|---|
| 建号者真实 IP | **拿不到**。docker 端口映射把所有来源 NAT 成网桥网关（如 `172.22.0.1`）。 |
| User-Agent | **拿不到**。默认 access log 只记 method/path/status/耗时，不记 UA；历史请求不可回溯。 |
| 谁调用的 | **拿不到**。`user` 表不记创建者；审计功能默认关闭（`/admin/audit-logs` 与 `/api/v1/admin/audit_logs` 均 404）。 |
| 用了哪个凭据 | 只有间接线索：token 的 `last_used_at`。 |

**证明「IP 字段零区分度」只需一步**：自己发一个普通请求，再读同一份日志——如果显示的也是那个网关
IP，这个字段就彻底没用了。先做这一步，再决定要不要继续挖；否则很容易把「网关 IP」当成「内网某人」。

同理，`sudo` 需密码、`grep` shell 历史零命中，都不等于「没人操作过」——可能是别的容器、别的账号、
或脚本早就删了。**不要把这些阴性结果写成结论。**

## `last_used_at` 不能直接当证据

它只记「最近一次用」，**不记用途**。必须回日志看那一刻打的是哪个端点：

- 若那几次是 `git-upload-pack`（clone/fetch）→ 不能据此指认它建了号；
- 只有落在 `admin/users` / `collaborators` 上的时间才能关联。

`scope=all` 的 admin token 在多端流转时是更大的洞（能建号 / 删号 / 改权限 / 删仓）。
**它属于别人的凭据时只上报、不自行轮换**——轮换会连带弄挂用它的一切自动化。

## 能查到的、也最有价值的是请求序列

把窗口内所有写操作拉出来，看**顺序**。典型建号脚本的指纹：

```
PUT  …/collaborators/<login>            422   ← 先授权，发现用户不存在
POST /api/v1/admin/users                201   ← 回头建号
PUT  …/collaborators/<login>            204   ← 再授权
GET  …/collaborators/<login>/permission 200   ← 建完立刻读回自查
```

人手动不会「先授权失败再回头建号」，也不会建完立刻 GET 自查 ⇒ **带重试 + 事后校验的脚本**，
即「某个持 admin 凭据的 agent」。把范围缩到这一层，比找一个 IP 有用得多，也足以支撑后续处置。

同窗口里夹一次 `401`（凭据试错）也是脚本特征——人失败一次会先去看文档，脚本会直接换一个再试。

拉日志的命令（容器名与时间窗口按实际改；**注意时区**，容器日志可能是 UTC，账号 `created` 是 +08:00）：

```bash
sudo -n docker logs gitea --since <ISO> --until <ISO> 2>/dev/null \
  | grep -E " (POST|PUT|DELETE|PATCH) " | grep -vE "internal/hook|git-upload|assets"
```

## 时间线对账：建号早于任务书

拿账号 `created` 对任务书的提交时间：

```bash
git -C <bus-clone> show -s --format="%h %cI %an %s" <task_commit>
```

**早于落单** ⇒ 有人凭提前知情执行（另一个 agent 抢跑、或看到群消息先动了）。这是独立的异常信号，
和「权限给得对不对」无关。

## 处置

1. **禁用（可逆），不删号**：`PATCH /api/v1/admin/users/<login> {"active":false}`，回读 `active=false`。
   协作者授权保留，`active:true` 一句话恢复——成本为零。
2. **实测禁用生效**：拿该账号的 token 打 API 应回 `403 This account is prohibited from signing in`
   （区别于 token 吊销的 `401 invalid username, password or token`）。
3. **上报 owner 拍板**：账号去留、要不要重建、`scope=all` 的 token 要不要轮换——都是 owner 的决定。
   回执里写清「已禁用 + 可逆 + 实测证据」，不写推测。
4. 重建时走「全新账号 + 重新授权 + 重发 token」，来源链才 100% 在自己手里。
