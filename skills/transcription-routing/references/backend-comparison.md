# Backend comparison & how to re-measure

Never quote these numbers as universal — they were measured on one sample, one host, one
provider pricing sheet. Re-run the measurement for the user's own content before recommending.

## How to measure

1. Generate a labelled sample with a TTS engine and a fixed script. Include the things that
   break: proper nouns (brand/people names), digits with units, mixed punctuation, a filler word.
2. Run every candidate. Record: transcription, error count against ground truth, wall time,
   and the endpoint's reported cost.
3. Diff carefully — a plausible-looking error (a real word, wrong word) is the dangerous one and
   easy to skim past.

## What typically separates the tiers

| Property | Cloud small/turbo tier | Cloud flagship ASR | Local small model |
|---|---|---|---|
| Accuracy on Chinese proper nouns | 1 error in a few | 0 errors | 2–3 errors (同音 substitutions) |
| Latency (short clip) | seconds | seconds | tens of seconds (CPU) |
| Cost | per second, often negligible | per second, higher | free |
| Offline | no | no | yes |

The decision usually reduces to: **cloud cheap tier as primary, local as offline fallback, and
a human correcting names either way.** Say that plainly instead of declaring one "best".

## Cost framing that lands with users

Quote cost per *second of audio* and translate to "how many minutes/hours until the credit is
gone". Users with a prepaid balance need that arithmetic, not a per-token rate.

## Known accuracy traps

- Chinese homophone substitutions: 证/正, 十/亿, 深证/深圳, 成/城. Always spot-check names.
- Whisper-family models may emit **Traditional** characters for Simplified input — normalize
  before diffing, or you will over-count errors.
- A pure tone or silence yields an empty string with a successful status — that is not a
  working backend, and not a failing one either. Use speech content in every probe.

## Free tiers

When a user mentions a free quota, check the *actual* model list for `:free`-suffixed ids
instead of assuming a brand covers audio. Many free tiers are text-only, and a model whose
name implies multimodality may still reject audio input with an empty upstream response.
Verify with a real clip before promising it works.
