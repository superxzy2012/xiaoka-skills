---
name: transcription-routing
description: Pick and route a speech-to-text backend (cloud vs local).
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [transcription, asr, whisper, audio, fallback]
    related_skills: [remote-browser-cdp-bridge]
---

# 转写后端选型与路由

Pick a speech-to-text backend, prove which one is actually accurate on the user's content,
and route between them so a network blip never silently produces garbage.

Use when: transcribing video/audio for notes or search; choosing between a cloud ASR API and a
local model; a transcription step is part of a larger ingest/download pipeline.

## When to Use
- Any pipeline whose output depends on speech-to-text (video → notes is the common case).
- The user asks "can I use X for transcription" or "why is local better/worse".
- Cloud quota, cost, or connectivity is a constraint.

## Standing rules

- **Never write off a local model because one download failed.** Diagnose the root cause first —
  an unreachable source is usually DNS, a proxy setting, or a mirror, not an unavailable model.
  BOSS rejected an early "local model unavailable, abandoning it" conclusion; the actual cause was
  poisoned DNS and a working mirror existed. Report the evidence (status codes) and the fix.
- **Prove accuracy on the user's real content, not on a tone generator.** Build a short sample
  with known ground truth (TTS with a fixed script is fine), run every candidate, and diff.
  Names and numbers are the tell — they are what a downstream note gets wrong.
- **Make the fallback automatic and test it by breaking the primary.** Point the client at an
  unreachable endpoint and confirm the fallback produces text. A fallback never exercised is a
  guess.

## Procedure

1. **Enumerate candidates and get real prices/status** from the endpoint's model list, not from
   memory. Probe each with a tiny audio clip; several will answer and still be unusable.
2. **Build a labelled sample** with a TTS engine and a fixed script containing the hard parts
   (proper nouns, digits, mixed punctuation).
3. **A/B every backend on that sample**; record error count, latency, and cost per second.
   Local CPU transcription is typically far slower than cloud — include that in the report.
4. **Wire a router**: primary first, fallback on exception, log which path served the result.
5. **Verify the degradation path** by making the primary unreachable.
6. **Report the table** (backend / errors / latency / cost) and let the user pick the default.
   Do not silently choose on their behalf when the trade-off is real.

## Pitfalls

- **Cloud ASR endpoints may not validate the API key.** A bogus key can still return 200, so
  "invalid key" is not a usable failure-injection method — break the *network path* instead
  (unreachable host/port) when testing fallback.
- **Model ids on aggregators often need a `provider/model` prefix**; a bare name fails with a
  misleading "invalid model" error. Read the id list the endpoint actually returns.
- **Local `faster-whisper` can collide with a newer PyAV** (`open() got an unexpected keyword
  'metadata_errors'`) even for a plain WAV. Bypass its decoder: `ffmpeg -f s16le` to raw PCM,
  load with numpy, pass the float array to `transcribe()`.
- **Small local models garble Chinese proper nouns and digits** (证→正, 十一→亿, 深证→深圳).
  Fine for routing/drafting, not for notes that quote specifics. Always state this limit.
- **Whisper-family output may be Traditional Chinese**; normalize before diffing or storing.

## Depth
- `references/backend-comparison.md` — cost/latency/accuracy trade-offs and how to re-measure.
- `references/local-model-install.md` — mirror fix, cache paths, PyAV bypass recipe.
- `scripts/asr_router.py` — cloud-primary/local-fallback router skeleton with the failure path built in.
