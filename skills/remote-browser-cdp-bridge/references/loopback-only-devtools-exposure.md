# Exposing a loopback-bound devtools port to the LAN

Chromium's remote-debugging port binds to `127.0.0.1` on current releases. Passing
`--remote-debugging-address=0.0.0.0` does **not** change this — the flag is ignored, and
relaunching with the flag (PowerShell, `cmd /c start`, different arg quoting) will keep
producing a loopback-only listener. Stop retrying launch flags and relay the port instead.

## Symptom triage before touching the firewall

| Result of `Test-NetConnection`/socket connect from the client host | Meaning | Fix |
|---|---|---|
| `Connection refused` | nothing bound to that port | relay / relaunch — a firewall rule changes nothing |
| `Connection reset by peer` | relay/portproxy is listening but **no CDP service behind it** — browser closed or debug port never came up | restart the browser; relay and firewall are fine |
| connect OK, then read hangs or times out | port is listening, packets filtered | firewall allow rule |
| connect OK and `/json/version` returns JSON | working | none |

`Connection refused` is the one that wastes turns: it looks identical to "the app is down" and
invites firewall edits that cannot possibly help.

`Connection reset by peer` wastes turns differently: it reads like a working relay, so the
instinct is to keep editing firewall/portproxy rules that are already correct. The signature is
that the relay port answers while the **backing port has no listener at all** — prove that from
the browser host with `netstat` (see below) and the fix is one browser restart, not a config edit.

## Which side broke: two netstat rows settle it

Check **both** ports from the browser host in one command:

```cmd
netstat -ano | findstr LISTENING | findstr /R /C:":9223 " /C:":9224 "
```

- relay port listening + backing port missing → the browser is down; relaunch it.
- both listening, but the client gets reset → something is holding the backing port that is
  not a browser (`OwningProcess` from the `Get-NetTCPConnection` form above identifies it).
- both listening and the client still fails → the firewall rule is missing or scoped to another
  profile; that is the only case a firewall edit fixes.

Use **distinct** ports for the internal devtools port and the relayed LAN port specifically so
this two-row comparison is possible at all.

## Command availability on the browser host under a non-admin account

Diagnosis often runs as an unprivileged automation user, where the obvious commands are denied.
Know which fallbacks are real before spending turns on retries:

| Command | Non-admin result | Use instead |
|---|---|---|
| `Get-NetTCPConnection` | `CimJobException: 无法连接到 CIM 类` | `netstat -ano \| findstr LISTENING` |
| `Get-CimInstance` | PermissionDenied | `netstat -ano` |
| `tasklist` / `tasklist /FI` | 「拒绝访问」, even for your own processes | the PID column of `netstat -ano` |
| `netsh interface portproxy show all` | works — reads fine unprivileged | keep using it; it is the fastest read of the relay topology |
| `whoami`, `hostname`, `$PSVersionTable` | works | — |

So the reliable unprivileged sequence is: `netstat` for listeners and PIDs, `netsh ... portproxy
show all` for the relay table, and escalate to `Get-NetTCPConnection` / `tasklist` only when the
PID actually has to be resolved to a name.

## Sending a multi-line script over ssh without quoting damage

A command has to survive three parsers: the local shell, the remote Windows shell, then the
PowerShell argument parser. Every hand-quoted variant breaks somewhere —
`powershell -Command "..."` loses `$r.Content` to the local shell, `-File path.ps1` fails
because ssh carries no file transfer, and stdin redirection lands in the wrong shell.

Base64 the script as UTF-16LE and hand it to `-EncodedCommand`, which is pure base64 and needs
no escaping at any layer:

```bash
ENC=$(iconv -f UTF-8 -t UTF-16LE script.ps1 | base64 -w0)
ssh -i KEY user@host "powershell -NoProfile -EncodedCommand $ENC" | tr -d '\000'
```

`base64 -w0` matters — the default wrapping splits the argument. `tr -d '\000'` strips the NUL
bytes that UTF-16LE introduces, which otherwise corrupt output containing non-ASCII text.
Output may still be mojibake under a non-UTF-8 console code page; set
`[Console]::OutputEncoding = [Text.Encoding]::UTF8` in the script when readability matters.
Execution is unaffected by the code page.

Keep remote diagnostics read-only and idempotent: probe → collect → print plain lines. Do not
have a remote script install or reconfigure anything — that needs admin anyway, and a failed
write leaves a messier remote host than the one you were sent to fix.

## Windows relay (verified shape)

```powershell
# 1) Launch the dedicated automation profile normally — devtools lands on 127.0.0.1:<p1>
$dst = "$env:LOCALAPPDATA\ChromeCDP"
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  -ArgumentList "--remote-debugging-port=9223","--user-data-dir=$dst"
Start-Sleep -Seconds 8

# 2) Relay loopback:<p1> -> LAN:<p2>
netsh interface portproxy add v4tov4 `
  listenaddress=0.0.0.0 listenport=9224 `
  connectaddress=127.0.0.1 connectport=9223

# 3) Allow the relay port inbound
New-NetFirewallRule -DisplayName "CDP-fwd-9224" `
  -Direction Inbound -Action Allow `
  -Protocol TCP -LocalPort 9224 -Profile Any

# 4) Verify locally BEFORE handing back to the user
curl.exe http://127.0.0.1:9224/json/version
```

Step 4 must return the browser JSON. If it does not, the relay is wrong — do not ask the user
to test from their laptop.

Use **different** ports for the internal devtools port and the relayed LAN port. Keeping them
distinct makes "which side broke" a one-line check instead of a debugging session, and stops the
relay rule from shadowing a port some other app already owns.

## Proving it bound correctly (the check that ends the guessing loop)

```powershell
Get-NetTCPConnection -LocalPort 9223 -State Listen |
  Select-Object LocalAddress,OwningProcess
```

- `LocalAddress = 0.0.0.0` → directly reachable, no relay needed.
- `LocalAddress = 127.0.0.1` → loopback only; relay required. This single field settles it,
  so read it rather than inferring from a failed remote connect.

`OwningProcess` also settles "is my browser even alive" in the same query — a `0.0.0.0` row with
no such process means something else grabbed the port.

## Ownership and cleanup

`portproxy` entries and firewall rules **persist across reboots**. Before adding a new pair,
delete stale ones (`Get-NetFirewallRule -DisplayName "*9222*" | Remove-NetFirewallRule`,
`netsh interface portproxy delete ...`) — an old rule scoped to a stale address silently
blocks the new one, and the failure looks like a browser problem.

## Identity of the relay is invisible to the client

The relayed `/json/version` reports the internal `webSocketDebuggerUrl` with `127.0.0.1` as the
host. That host is unreachable from the client, so the websocket handshake fails even though the
HTTP probe succeeded. Rewrite the host in the ws URL to the client's reachable address
(`ws_url.replace("127.0.0.1", "<relay-host>")`) before connecting, and keep
`suppress_origin=True`.

If the HTTP probe passes but the websocket 404s or hangs, this host rewrite is the first thing
to check — the port is fine and the URL is wrong.
