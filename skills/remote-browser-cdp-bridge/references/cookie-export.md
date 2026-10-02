# Cookie export (dual format)

Goal: pull the session out of the browser once so CLI tools can use it without a browser.

## Where cookies come from

```python
b = p.chromium.connect_over_cdp(CDP_URL)
allc = b.contexts[0].cookies()      # list[dict]: name, value, domain, path, secure, expires
```

## Two formats, two consumers

**Netscape `.txt`** — for yt-dlp, curl, requests-style tools.

```
# domain \t includeSubdomains \t path \t secure \t expires \t name \t value
```

- `includeSubdomains` = `TRUE` when the domain starts with `.` (a cookie scoped to the TLD).
- `expires`: session cookies report `-1`. yt-dlp logs `skipping cookie file entry due to
  invalid expires at -1` and drops those entries. Either omit them or write a far-future
  timestamp; a few drops is usually tolerable, but check which cookies actually survived.
- **This format puts session secrets in a plaintext file.** Keep it out of any repo/vault that
  syncs elsewhere, and never paste its contents into chat.

**Raw JSON** — for replaying through playwright (`context.cookies()` shape) or debugging which
cookies exist per site.

## Per-site files, not one blob

Partition by registrable domain so a tool can be pointed at exactly one site's jar:

```python
SITES = {"<site>": [".<domain>", "www.<domain>"], ...}
for name, doms in SITES.items():
    sel = [c for c in allc if any(d in c["domain"] for d in doms)]
    # -> <name>.json  and  <name>_cookies.txt
```

## Hygiene

- Re-export after every re-login; stale jars produce confusing "logged out" bugs.
- A large cookie count is **not** evidence of a live session — see the guest-session probe in
  `location-and-auth-ceilings.md`.
- On abandoning a site, delete both files for it.
