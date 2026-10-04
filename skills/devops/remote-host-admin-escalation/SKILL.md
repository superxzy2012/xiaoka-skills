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
2. **Filesystem reach.** Can you write the host's data directories from inside your container?
   Look for a compose file, an app-data root, or a task-drop directory someone already wired up.
3. **A bridge you already have.** A browser with a debug port, a desktop app, a message-bus
   inbox. If a task-drop directory exists but you cannot write it, check whether the writer is
   on the other side and reachable through a rung below.
4. **The host's own management API.** Vendor panels ship a front-end bundle that names every
   endpoint — see `remote-browser-cdp-bridge` for the recon recipe.
5. **Hand over.** One command.

Rungs 2–4 are where sessions usually quit early. Do not.

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
- **A stale credential is not a wrong password.** A share that worked months ago failing with a
  timeout is an expired account, not a typo — do not keep retrying variants of it.

## Depth

- `references/hermes-container-boundary.md` — the write-permission map from inside the Hermes
  container, and how to re-derive it when it changes.
