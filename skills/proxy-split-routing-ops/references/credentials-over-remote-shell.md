# Getting a secret to a remote shell without leaking it

Read this when a script must authenticate somewhere using a credential you hold, and the script
runs on another host.

## The trap

`subprocess.run(..., env={**os.environ, "TOKEN": value})` sends the variable to the **local**
process. `ssh host 'bash script.sh'` starts a fresh login shell on the far side, which inherits
nothing from your local environment. The remote script then reads an empty variable and the service
answers `{"message":"token is null"}` — while the local script, the SSH command, and your logs all
look correct.

`SendEnv` in `ssh_config` only works for variables the server's `sshd` also lists in `AcceptEnv`;
it is off by default and not a path worth fighting.

## The pattern that works

Build the script with the value interpolated **into an export inside the script body**, ship the
script as one base64 blob, and scrub the value from captured output:

```python
import base64, re, subprocess

remote = r'''
export API_TOKEN="__TOKEN__"
URL="https://host/api?token=${API_TOKEN}"
curl -s -m 20 -A 'clash-verge/v1.6.0' -o /tmp/sub.yaml -w 'http=%{http_code}\n' "$URL"
# report shape, never the secret
echo -n "bytes="; stat -c%s /tmp/sub.yaml
echo -n "nodes="; grep -cE '^\s*-\s*\{' /tmp/sub.yaml
'''
remote = remote.replace("__TOKEN__", TOKEN)
blob = base64.b64encode(remote.encode()).decode()

r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-i", KEY, f"user@host",
                    f"echo {blob} | base64 -d | bash"],
                   capture_output=True, text=True, timeout=120)

print(re.sub(r'first8ofTOKEN\w*', '<REDACTED>', r.stdout))
```

Two things make this safe enough in practice: the secret never appears in `argv` (so it is absent
from `ps` and from the SSH command line in any log), and the redaction step keeps it out of the
transcript you paste back.

## Rules

- **Never assert that a local env var reached the remote shell.** Echo the variable's *length* on
  the far side first; that single check distinguishes "wrong credential" from "credential never
  arrived".
- **Report shape, not values.** Byte count, node count, HTTP status, and content type confirm a
  fetch worked. Never print a token, password, cookie value, or node credential.
- **A JSON body naming a missing parameter is a delivery bug, not a bad credential.**
  `token is null` means the variable was empty on arrival; `token invalid` means it arrived and
  was rejected. They need opposite fixes.
- **A `403` that survives a User-Agent change is genuinely auth or IP.** Panels commonly require
  a client UA; once set and still 403, stop varying the UA and check whether the subscription is
  expired, rate-limited, or bound to a client IP.
- **Once it works, move the credential out of your notes.** Store it on the target as a
  `chmod 600` file referenced from config, so the next session reads a file instead of
  reconstructing a value that has now appeared in several transcripts.
