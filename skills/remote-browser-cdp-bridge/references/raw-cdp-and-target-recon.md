# Raw CDP + target recon

Two jobs this covers:
1. Driving a remote Chromium **without** playwright (raw CDP over websocket).
2. Using that browser to **recon an unauthenticated target** — find its real ports,
   real API prefix, and whether the user's browser holds a usable session.

---

## 1. Raw CDP without playwright

Use this when `connect_over_cdp` is unavailable, the wrapper's JS eval returns junk, or you
need byte-level control. Stdlib-only option: `pip install websocket-client`.

**Always open your own tab. Never drive the user's existing tabs.**

```python
# HTTP PUT creates a tab; GET is deprecated on newer Chrome builds.
tab = json.loads(subprocess.run(
    ["curl", "-s", "-X", "PUT", f"http://{CDP}/json/new?about:blank"],
    capture_output=True, text=True, timeout=30).stdout)

ws = websocket.create_connection(tab["webSocketDebuggerUrl"],
                                 timeout=15, suppress_origin=True)
```

`suppress_origin=True` omits the `Origin` header entirely. Many Chrome builds reject CDP
handshakes that send an `Origin` but accept ones that send none — if the connect throws, try
both with and without it before concluding the port is closed.

Request loop: send `{"id": N, ...}`, then read frames until one comes back with that same
`id`. Events (`Page.*`, `Runtime.*` notifications) interleave — you must consume and discard
them, and set a short socket timeout so a missed event cannot hang the call.

Close the tab afterwards: `curl -s http://{CDP}/json/close/<id>`.

### Re-measure capabilities every session

Do NOT trust a stored conclusion that some CDP method is "blocked". Chrome restarts, flags
change, policies get reapplied. Run a three-line probe on a fresh tab and read the answers:

| Probe | Healthy result |
|---|---|
| `Runtime.evaluate` → `1+1` | `2` |
| `Page.navigate` → an intranet URL, then read `document.title` | non-empty title |
| in-page `fetch('/')` → status | `200` |

A stale negative here costs a whole session, because it makes you hand work back to the user
that you could have done.

---

## 2. Recon a target you cannot authenticate against

**Never guess ports.** Guessing burns turns and produces confident wrong answers. Scan once,
then identify each open port by its response fingerprint.

Fingerprint tells:
- `Location: /desktop/?os=ugospro` → vendor management panel
- `<title>Gitea: ...` → a git forge, not the thing you assumed
- `Www-Authenticate: Basic realm="Restricted"` → a protected API on a nonstandard port
- plain `text/html` body on a path you invented → SPA catch-all, see below

**HTTP 200 is not proof an endpoint exists.** Single-page apps return `200 text/html` for
every unknown path via the catch-all route. A real API answers with its own content type
(`application/json`) or `404`. Always print status **and** content-type together; a bare
status code will read as a false positive.

### Pull the front-end bundle — it is the API map

Vendor panels expose nothing in docs. The shipped JS bundle names every endpoint.

```python
# Do this INSIDE the browser. curl from your host often returns 0 bytes
# (no Referer, or the bundle is served with headers curl won't send).
js_len = c.js("fetch(BUNDLE_URL).then(r=>r.text()).then(t=>t.length)")
paths = c.js(f"""fetch({BUNDLE_URL!r}).then(r=>r.text()).then(t=>{{
  const m = [...t.matchAll(/["'`](\\/[a-zA-Z0-9\\/_\\-]*(?:system|container|docker|image|compose)[a-zA-Z0-9\\/_\\-]*)["'`]/gi)]
    .map(x => x[1]);
  return [...new Set(m)].sort().join('\\n');
}})""")
```

If nothing matches in the entry bundle, enumerate lazily-loaded chunks — they only appear
after login:

```python
c.js("performance.getEntriesByType('resource').filter(e=>e.name.endsWith('.js')).map(e=>e.name).join('\\n')")
```

Then read the actual login state from the DOM, not from storage keys:

- `location.hash` ending in `#/login/...` means **not logged in**, no matter what
  `localStorage` holds.
- `localStorage` holding an `appKey` / session blob is **not** an authenticated session —
  those are written before login completes.
- Enumerate `document.cookie` and probe one endpoint that requires auth for the real verdict.

If the panel needs login and the user's browser is not logged in, **stop**. That is a
credential boundary, not a puzzle — see the handoff rule below.

---

## 3. Handing the user an access command

When the only remaining step needs the user's own privileges, hand over one copy-pasteable
command — never a paragraph of manual steps.

**Derive any key material from the private key, never from a file you happened to read.**
A `known_hosts` entry looks exactly like a public key and will paste cleanly while granting
nothing, so the user sees success and you see silence.

```bash
ssh-keygen -y -f ~/.ssh/id_ed25519          # authoritative
ssh-keygen -lf ~/.ssh/id_ed25519           # fingerprint to assert on
```

Before sending, extract the key back out of the finished text and compare its fingerprint to
the private key's. Then state plainly which thing you could not do and why, and what you will
do the moment access exists — one line each, no apology.
