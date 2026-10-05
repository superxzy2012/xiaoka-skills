# Exposing a loopback-bound devtools port to the LAN

Chromium's remote-debugging port binds to `127.0.0.1` on current releases. Passing
`--remote-debugging-address=0.0.0.0` does **not** change this — the flag is ignored, and
relaunching with the flag (PowerShell, `cmd /c start`, different arg quoting) will keep
producing a loopback-only listener. Stop retrying launch flags and relay the port instead.

## Symptom triage before touching the firewall

| Result of `Test-NetConnection`/socket connect from the client host | Meaning | Fix |
|---|---|---|
| `Connection refused` | nothing bound to that port | relay / relaunch — a firewall rule changes nothing |
| connect OK, then read hangs or times out | port is listening, packets filtered | firewall allow rule |
| connect OK and `/json/version` returns JSON | working | none |

`Connection refused` is the one that wastes turns: it looks identical to "the app is down" and
invites firewall edits that cannot possibly help.

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
