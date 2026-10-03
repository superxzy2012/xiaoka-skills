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
   **Run the local ingest script first; do not hand-roll a platform item-info API call.**
   Those endpoints get encrypted or retired without notice — douyin's
   `web/api/v2/aweme/iteminfo` returns `status_code 11110 / encrypt_data_miss` for
   *both* image-post and video ids, so a URL shape that looks right yields an empty
   item list. See `references/platform-routes.md` for the verified per-platform route.
2. **Download with the site's cookie jar.** A logged-out downloader gets a guest page, rate-limit
   walls, or an HTML file named `.mp4`.
3. **Transcribe through the router** (see the `transcription-routing` skill) and keep the
   backend/cost that served it.
4. **Extract keyframes** (roughly one per 15s) so a future reader can verify visual claims.
5. **Write the note** = frontmatter (title, source_url, platform, platform_id, author, duration,
   date, tags) + one-line summary + verbatim transcript + key points + actionable follow-ups.
6. **Archive frames** beside the notes; keep the video only when asked (it is the large part).
7. **Correct proper nouns against frame OCR, then verify the OCR result independently.**
   ASR mangles exactly the tokens that make a note findable later: a product name became
   「cogee」and 「探索」in the same transcript, `Claude` became「Cloud」, and a GitHub org
   read `om-ai-lab` became「om-al-lab」. Cropped screenshots carry the real spelling, so OCR
   the keyframes and diff against the transcript.
   **OCR is a candidate source, not an authority** — that misread org name returned
   `Not Found` when queried directly and only resolved via a repository search that found
   the correct spelling. Confirm any identifier that will be cited with a live lookup.
   Fix the transcript's wording in the note and mark the corrections inline.

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
- **On screen-recording videos, frame OCR cannot recover the project name.** Burning-in subtitles
  sit at low contrast and OCR reads only scattered fragments; cropping and upscaling the region
  that should hold the identifier makes it *worse* (blur, not resolution). For those, treat the
  transcript's candidate names as hypotheses and confirm each with a live lookup — never assert
  the tool in the notes from OCR alone.

## Depth
- `references/platform-routes.md` — verified fetch route per platform, frame-OCR corrections, batch-OCR cost.
- `scripts/ingest_one.py` — the single-link ingest flow end to end, ready to adapt.

## Open-source project videos: verify, don't transcribe

Many of these videos are project showcases. A transcript plus a star count is not a finding —
the sponsorable errors live in the claim the video is making.

For every project named in the note, confirm against live data and write a FACT/claim table:
repo owner/name, star count, license, last push, and whether it is still maintained.
The claims that most often break:

- **"36K stars"** — often right, but read it off the API at the same moment you write the note so
  the number has a date attached.
- **"Docker deployment"** — check the official README/docs, not just the video. A desktop
  Electron app's docs listing only Linux/macOS/Windows/Android with no Docker mention means
  there is no official image; the video is running a third-party one. Name the official
  component when one exists and it does something narrower (a sync server is not a media server).
- **"Open source" with no license visible** — see below.

**Never resolve a license from the GitHub API alone.** `license.spdx_id` returns `NOASSERTION`
whenever the LICENSE file carries custom prose above the standard text, which reads as
"unlicensed". Pull the LICENSE text and judge it yourself. Beware the reverse trap too: a bare
`noncommercial` substring matches AGPL-3.0 section 6(b) ("allowed only occasionally and
noncommercially"), which is a condition on *offering source*, not a ban on commercial use —
that misread will wrongly disqualify a perfectly AGPL project.

When the video promotes a tool this machine already has a skill for, diff them explicitly: a
local skill and an upstream project can share a name and be entirely different things (local one
a Markdown workflow template, upstream a TypeScript web app). Say so in the note rather than
letting the name collision imply coverage.

## Archiving

Frames, transcripts, OCR scripts, and pulled source all belong under
`15-小卡工作区/<workspace>/开源源码/<project>/` — `cache/scratch/` is pruned after 24h idle,
so anything left there will need re-downloading. Copy artifacts in, then fix the path references
inside the note so they point at the permanent location.
