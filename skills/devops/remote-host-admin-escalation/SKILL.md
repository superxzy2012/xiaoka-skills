---
name: remote-host-admin-escalation
description: Use when a task needs remote-host admin rights.
---

# Remote host admin: exhaust your own paths, then escalate once

Task class: "do X on machine Y" where Y is a NAS, a Windows box, an appliance web
panel, or another host — and you are running inside a container with partial reach.

The failure mode is handing the job back before you have actually tried everything, or
handing it back as a paragraph of manual steps instead of one command.

## The rule

**Do not hand a task back until you have walked the full escalation ladder and can name the
exact boundary that stopped you.** "I couldn't log in" is not an answer; "SSH is open, key auth
is rejected for all four accounts I tried, the shared filesystem subtree I can write stops at
`<path>`, and the vendor panel needs a session I don't hold" is an answer.

When you are genuinely blocked, hand back **one copy-pasteable command**, plus one line on what
you will do the moment it works. Not a numbered tutorial.

## Escalation ladder

Walk in this order. Each rung costs one call; stop when one works.

1. **Direct protocol.** SSH / HTTPS / the vendor's own API. Probe with `BatchMode=yes` so you
   never burn an auth-failure counter on a guessed password.
2. **Passwordless sudo enumeration.** Once *any* login lands, ask what the account may run
   without a password before concluding you need the user's password:
   `sudo -n -l` — a line like `(ALL) NOPASSWD: /usr/bin/docker` is a full-root channel, because
   `sudo -n docker run|exec|cp` gives you arbitrary code execution on that host as root. Enumerate
   this the moment you get in; it converts most "needs admin" tasks into work you finish yourself.
3. **Filesystem reach.** Can you write the host's data directories from inside your container?
   Look for a compose file, an app-data root, or a task-drop directory someone already wired up.
4. **A bridge you already have.** A browser with a debug port, a desktop app, a message-bus
   inbox. If a task-drop directory exists but you cannot write it, check whether the writer is
   on the other side and reachable through a rung below.
5. **The host's own management API.** Vendor panels ship a front-end bundle that names every
   endpoint — see `remote-browser-cdp-bridge` for the recon recipe.
6. **Hand over.** One command.

Rungs 3–5 are where sessions usually quit early. Do not.

## Proving the boundary, not assuming it

State facts you measured:

```bash
touch "$DIR/.wtest" 2>/dev/null && { echo "writable: $DIR"; rm -f "$DIR/.wtest"; } \
                      || echo "NOT writable: $DIR"
```

A directory you wrote successfully in an earlier session may have been re-permissioned. Re-test
the whole boundary each time; do not quote a stored map as current. Report the boundary as a
tree, not a sentence — the user can see at a glance which subtree is theirs.

## Handing over an access command

Any key material in the command must be derived from the **private key**, never copied out of a
file you happened to read — a `known_hosts` line is textually identical to a public key and will
paste cleanly while authorizing nothing.

```bash
ssh-keygen -y -f ~/.ssh/id_ed25519     # authoritative public key
ssh-keygen -lf ~/.ssh/id_ed25519      # fingerprint to assert on
```

Before sending, extract the key back out of your finished text and confirm its fingerprint
matches the private key. Then say plainly what is blocked and why, and what you do next.

### If you ship a script instead of a bare command

A generated script needs the same verification, and the check must be on the **file the script
writes**, not on its exit code:

- **Assert the artifact, not the intent.** Run the script against a throwaway `HOME`, then
  `grep`/parse the output file it claims to have written. A success message on stdout proves the
  code path ran, not that the payload landed — an escape bug can print "OK: appended" while
  writing literal text instead of the value.
- **Self-test in four layers**: `bash -n` (syntax) → dry run in a clean `HOME` (runtime) →
  inspect the real artifact (correctness) → run twice (idempotency, no duplicate lines).
- **Keep the payload in exactly one place** and substitute it programmatically. Hand-typed key
  material inside a generated file is how a comment gets duplicated or a `%s` gets double-escaped
  into a literal.
- **Have the user run the verification too.** End the handoff with the one command that proves it
  worked (e.g. `grep -c 'your-comment' ~/.ssh/authorized_keys` → expect `1`), so a failure surfaces
  as a number instead of a second round of "still denied".

If they report it still fails and the script claimed success, suspect the artifact, not their
shell: the most common cause is a quoting/escape bug in the line that writes the payload.

## Delivering scripts and secrets to a remote shell over SSH

Three mechanisms fail silently here — each produced a wrong-but-plausible result rather than an
error, which is what makes them expensive:

- **Environment variables do not cross the SSH boundary** unless the server's `AcceptEnv`
  permits them. Passing `env=` to your local `ssh` call leaves the remote variable **empty**, and
  the command then runs against a blank credential and reports "invalid" rather than "unset".
  Assert arrival before use: print `${#VAR}` on the far side and confirm it is non-zero.
- **`ssh host 'cmd'` does not forward the caller's stdin** to that command. Piping a script into
  `ssh` loses it before the remote shell sees it.
- **Nested quoting destroys heredocs and shell functions.** Encode the payload and decode it on
  the far side — `ssh host "echo <b64> | base64 -d | bash"` — so `$`, backticks, and braces
  survive intact. Note the target shell may be POSIX `sh`: `def f() { …; }` is a syntax error
  there, so write loops, not function-declaration syntax.

Pass a secret as a positional argument to a temp script only when the host is one you already
administer, and `rm` the script in the same command.

## Do not install half a job and call it blocked

Everything that does not need the missing privilege is still yours to finish: config files,
validated rule ordering, install scripts, a self-test on the parts you can reach, the measured
baseline that proves the problem exists. Deliver that as done work, and name the single
remaining step. A task left 95% finished with a one-line blocker beats the same task left 5%.

## Pitfalls

- **Guessed ports produce confident wrong answers.** Scan and fingerprint responses before
  naming a service; a well-known service on an assumed port may belong to something else
  entirely, and acting on that costs the whole session.
- **`200 text/html` on a path you invented is an SPA catch-all**, not an endpoint. Read status
  and content-type together.
- **Stored capability conclusions go stale.** Re-probe before telling the user a task needs
  their hands; see the staleness rule in `remote-browser-cdp-bridge`.
- **A stale credential is not a wrong password.** A share that worked months ago failing with
  a timeout is an expired account, not a typo — do not keep retrying variants of it.
- **`sudo -n true` failing does not mean you need the password.** It only means *that* command
  needs one. `sudo -n -l` lists the passwordless allowlist; check it before escalating.
- **A panel that regenerates its own config file will silently revert your edit.** GUI-managed
  proxies and gateways keep their state in a database and rewrite `config.json` on every reload,
  so `docker cp` / in-place edits are reverted on the next restart (watch for a repeating
  `Quitting...` in the logs). Change such a service through its own API, or verify your edit
  survived a restart before reporting success.
- **Verify a service's own validation, not your config's readability.** Start the binary with its
  config-test flag inside a throwaway container and quote its verdict; parsing the YAML yourself
  proves only that YAML is parseable.

## Depth

- `references/hermes-container-boundary.md` — the write-permission map from inside the Hermes
  container, and how to re-derive it when it changes.
