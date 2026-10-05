# Getting admin on a host you only share a browser with

Read this when a task needs real privileges on another machine (install a container, edit system
config, open a port) and you currently have none. The goal is to get to the *first* action that
needs credentials, then hand off — not to keep probing.

## Establish the permission boundary in one sweep, then stop

Probe every channel once, in a single pass, and record the result. Do not keep re-probing
across turns while the answer is the same.

| Channel | Probe | Meaning when it fails |
|---|---|---|
| SSH to the target | `ssh -i <key> -o BatchMode=yes <user>@<host> 'id'` over the plausible usernames | port open + `Permission denied` = you need the user to authorize you |
| Shared filesystem write | `touch <mount>/.wtest && rm <mount>/.wtest` | read-only mount = you cannot deploy anything there |
| Vendor control panel API | fingerprint the panel's real port (see below), then look for a container/service endpoint | unauthenticated 404 = needs panel credentials |
| Docker socket / data dir | `ls <mount>/@docker/containers` | `Permission denied` = no deploy path from here |
| Browser CDP | see `remote-browser-cdp-bridge` | useful for *reading*, not for privileged writes |

Then state the boundary plainly: which operations are impossible from here, and why. "I am in a
restricted uid and cannot write outside the mounted subtree" is a real answer; a fifth identical
`Permission denied` is not.

## Panel ports: never guess, fingerprint

A `200` on a guessed API path is usually the SPA catch-all, not an endpoint. Read **status and
content-type together** — `200 text/html` on every path means you are hitting the router.

Scan the likely ports once, then identify each open port by what it actually serves:

```bash
for p in 22 80 443 3000 5000 5001 6789 8000 8080 8443 9000 9090 2375 2376 9999; do
  timeout 3 bash -c "exec 3<>/dev/tcp/$HOST/$p" 2>/dev/null && echo "$p open"
done
curl -si -m 8 "http://$HOST:$PORT/" | head -12   # headers fingerprint the service
```

Headers that identify services: a `Location: /...?os=<name>` redirect names the vendor OS; a
`Www-Authenticate: Basic realm="Restricted"` means an API needing credentials; a
`Set-Cookie: i_like_gitea=` means that port is something unrelated entirely.

**A port you assumed is your own app may belong to something the user runs.** Confirm what a
port serves before building on it — assuming a port is the vendor panel and it is actually the
user's side project sends the whole task down the wrong path.

## A panel that owns its config will revert your edit

Management panels persist their state in a database and **regenerate the config file from it on
every reload**. Copying a modified config in with `docker cp`, or writing it on the host, then
restarting the service loses the edit silently — the file comes back byte-identical to the panel's
copy, and the symptom is "the change did not take" with no error anywhere. Repeated `Quitting…`
lines in the service log are the tell.

So: if a panel ships an HTTP API, the API is the only supported write path. Use the file only
when no panel owns it, and then confirm the write survived (`md5sum` before and after a restart)
instead of trusting the `cp` exit code.

Before treating that route as available, know whether you can authenticate. A `401` on the panel's
health or touch endpoint means it needs a session you do not hold: **ask the user for the panel
credentials, or ask them to import the subscription in the panel UI — do not guess passwords.**
An unauthenticated `404` proves nothing either way; authenticated routes are not in the bundle a
logged-out fetch returns.

### Find the panel's real port from inside the container

A service container on `NetworkMode: host` still advertises its **documented** port in your
head while binding a different one. Read what is actually listening:

```bash
sudo -n docker inspect <name> --format '{{.HostConfig.NetworkMode}}'          # host? then its ports are the host's
sudo -n docker exec <name> sh -c 'netstat -tlnp 2>/dev/null || ss -tlnp'      # ground truth
sudo -n docker inspect <name> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
```

Assume the panel's port from documentation is wrong until that scan says otherwise — a panel
listening on `3017` while every doc and every guess says `2017` costs an afternoon. And when a
container path is bind-mounted, the host-side source path is what persists across recreates;
editing a file only visible inside the container is editing a copy that a `create` will discard.

## The one-step authorization handoff

When the only thing standing between you and the task is credentials, hand back the *shortest
possible* privileged command and nothing else. No config to review, no paths to choose, no
second step. The user should paste one block and be done.

Target shape: create the key dir, append the pubkey, fix perms, print a confirmation count.

### Deriving the pubkey — never hand-copy it

`ssh-keygen -y -f <private>` output **already carries the comment field**. Concatenating a
comment onto it again yields `xiaoka@nas xiaoka@nas`, which SSH rejects while exiting 0 — the
handoff silently authorizes nothing and the failure surfaces later as a bare
`Permission denied`. Use the `ssh-keygen -y` output verbatim.

A `known_hosts` line pastes just as cleanly and authorizes nothing at all, because that key
belongs to whatever host fingerprinted last. Only the private key is a source of truth.

### Ship the handoff only after executing it

Before the user ever sees the command:

1. `bash -n` the block (syntax).
2. Run it with `HOME=$(mktemp -d)` so it writes into a throwaway dir — never touch a real `~/.ssh`.
3. **Read the produced `authorized_keys` back and grep it for the key comment.** Exit status and
   the script's own "OK: appended" stdout are not evidence — a script can report success while
   writing the wrong bytes. Generated-from-another-language blocks are where this bites: a
   `printf '%%s\n'` surviving one escaping layer emits the literal `%s`, so the file grows by one
   line, the run reports success, and the grant authorizes nothing while the next login fails with
   a bare `Permission denied`. Grep the artifact for a substring that only a correct write
   produces (`grep -c '<comment>'` must be exactly 1).
4. `ssh-keygen -lf` the produced `authorized_keys` **and** the private key; compare fingerprints.
5. Assert the comment appears exactly once.

Steps 3–5 are what catch the duplicate-comment, wrong-bytes, and truncated-key bugs. A
syntactically valid command that reports success is not a correct one — assert on the artifact.

If a login still fails after a green handoff, walk sshd-side state before re-shipping the
command: `ls -ld ~/.ssh`, `ls -l ~/.ssh/authorized_keys`, `stat -c '%n %U:%G %a'` on both, and
`sshd -T | grep -i authorizedkeys`. `StrictModes` rejects a group-writable directory or a
key file not owned by the login user, and a `#AuthorizedKeysFile .ssh/authorized_keys` line in
`sshd_config` means the comment means nothing. Separate "the bytes are wrong" (step 3) from
"the permissions or path are wrong" (this check) before changing anything.

### Scope the grant to the least privilege that works

Name the narrow group that suffices (e.g. the container runtime group) instead of root. If the
user's account already has it, the grant is a no-op and the task proceeds. Say how to revoke:
delete that one line from `authorized_keys`.

## State the blocker as a blocker

When the boundary is real, say the task is not done and name the exact permission missing.
Offering a config file or a script the user must run themselves is fine — presenting it as
*done* is not. Do not describe prepared work as a completed install.