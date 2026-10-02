# Local model install & troubleshooting

Local STT is worth keeping even when a cloud endpoint exists: no per-call cost, works offline,
keeps audio on-box. Install it before declaring it unavailable.

## Triage order (do not skip to step 3)

1. **Is the host actually unreachable, or just one address family?**
   ```bash
   curl -s -m 10 -o /dev/null -w "%{http_code}\n" https://<host>          # 000 = no route
   curl -4 -s -m 10 -o /dev/null -w "%{http_code}\n" https://<host>      # forces IPv4
   getent hosts <host> | head                                            # what IP did DNS pick
   ```
   A `getent` result in an unrelated vendor's range (e.g. a social-media CDN) means **DNS
   poisoning**, not an outage. Forcing IPv4 proves or disproves the address-family theory.

2. **Check mirrors before declaring defeat.** A package-host mirror that answers 200 and serves
   the model API is the fix. Try in this order: the vendor's official mirror, then a regional
   model hub.

3. **Only after mirrors fail** is a cloud default reasonable — and say *why* it failed, with
   status codes.

## Persistence

Put the fix in a sourced env file and load it from the shell profile so it survives new shells:

```bash
export HF_ENDPOINT=https://<mirror>          # mirror for model weights
export HF_HOME=<writable-cache-dir>          # must be writable; default may be read-only
export HF_HUB_DOWNLOAD_TIMEOUT=120
```

Verify the download actually happened (`du -sh "$HF_HOME"`) — the loader can report "ready"
from cache even when nothing was fetched this run.

## The PyAV decoder collision

Symptom: `faster_whisper` raises `TypeError: open() got an unexpected keyword argument
'metadata_errors'` from `av.open(...)`, for **any** input including plain WAV. The bundled
audio decoder is built against a different PyAV than the installed one.

Do not fight the pin. Bypass the decoder:

```bash
ffmpeg -i in.wav -f s16le -ar 16000 -ac 1 out.pcm
```
```python
import numpy as np
from faster_whisper import WhisperModel
audio = np.fromfile("out.pcm", dtype=np.int16).astype(np.float32) / 32768.0
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio, language="zh", beam_size=5)
text = "".join(s.text for s in segments)
```

Also set `OMP_NUM_THREADS` — an unbounded default can thrash small containers.

## Where a local model fits anyway

Drafts, routing decisions, bulk triage where a human will check names later. Keep cloud for
anything whose output is quoted or indexed.
