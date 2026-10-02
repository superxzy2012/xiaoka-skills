---
name: video-ingest-pipeline
description: Turn short-video links into real, cited Obsidian notes.
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [ingest, douyin, bilibili, obsidian, transcription, notes]
    related_skills: [transcription-routing, remote-browser-cdp-bridge]
---

# 短视频入库管线

Take short-video links and produce notes whose transcript is real, sourced, and auditable.

Use when: the user pastes a douyin/bilibili share link and says 入库/收藏/存知识库; a batch of
such links; or a task needs durable notes built from video content.

## When to Use
- One or many short-video share links destined for a shared knowledge base.
- Reusable pipeline needs: the user says 固化 after a successful manual run.

## Standing rules

- **The transcript is the source of truth; the summary is derived from it.** Never invent or
  "reconstruct" spoken content — a hallucinated transcript that looks real is the single worst
  failure mode here, and it has burned this user's library before (bulk notes that turned out to
  be fabricated). If transcription fails, write an explicit failure marker, not a plausible body.
- **Generate the skeleton, then read the transcript yourself and write the key points.** Do not
  have a second model summarize unverified ASR output into the final note without a check.
- **Write to the shared library's canonical directory for that platform**, with a
  frontmatter block and a link back to the original. Naming and location are what make the
  library navigable later.
- **When the user says 固化, ship a runnable script**, not a description of the steps, and
  re-run it (dry-run first) to prove the script path works — not just the manual path.

## Procedure

1. **Resolve the share link and fetch metadata in one call** — the platform id, canonical title,
   uploader, and duration all come from the downloader's metadata output.
2. **Download with the site's cookie jar.** A logged-out downloader gets a guest page, rate-limit
   walls, or an HTML file named `.mp4`.
3. **Transcribe through the router** (see the `transcription-routing` skill) and keep the
   backend/cost that served it.
4. **Extract keyframes** (roughly one per 15s) so a future reader can verify visual claims.
5. **Write the note** = frontmatter (title, source_url, platform, platform_id, author, duration,
   date, tags) + one-line summary + verbatim transcript + key points + actionable follow-ups.
6. **Archive frames** beside the notes; keep the video only when asked (it is the large part).
7. **Proofread proper nouns against the canonical title/uploader** before declaring it done —
   ASR mangles names (`WorkBuddy`→`WorkerBody`, `DeepSeek`→`Dingsick`) and the notes are indexed
   by those names.

## Pitfalls

- **Take the video id from metadata, not the URL.** Share short links (e.g. `v.douyin.com/<code>/`)
  contain no `/video/<id>` segment; deriving the id from the string yields an empty or wrong value
  that then propagates into frontmatter and the attachment folder name.
- **Strip `#hashtags` from the file name only.** Platform titles append topic tags; keep the full
  title in frontmatter so nothing is lost, but a 200-char name breaks wikilinks and paths.
- **Escape a regex character class when splitting on `#`** — a bare `#` inside `re.split` is a
  comment and silently returns the whole string.
- **Netscape cookie files**: session cookies with `expires = -1` get dropped by yt-dlp with a
  warning. Check that the cookies you actually need survived the export.
- **Writing outside the writable root fails for file tools** but not for shell `cp`/`ln`. Build
  the note locally, then copy into the vault; `os.makedirs` the destination dir first.

## Depth
- `references/note-format.md` — the frontmatter and section skeleton that makes notes searchable.
- `references/download-and-cookies.md` — cookie export, guest-vs-logged-in pitfalls, platform quirks.
- `scripts/ingest_one.py` — the single-link ingest flow end to end, ready to adapt.
