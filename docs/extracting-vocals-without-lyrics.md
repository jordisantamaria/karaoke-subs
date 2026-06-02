# Extracting vocals when we have NO lyrics (spoken parts / buried backing vocals)

Procedure for recovering sung/spoken parts that **are not in the official lyrics** and
that whisper, in normal mode, discards because they are mixed under the instrumental
(it classifies them as "music", not as vocals).

A typical example: a spoken passage in an interlude (e.g. 2:22–2:48) that was not in the
official lyrics in the booklet.

## Symptoms

- A gap with no subtitle in the video, but **when you listen there IS a voice**.
- whisper's normal transcription returns nothing in that stretch (it treats it as an interlude).

## Environment (already installed)

- A venv with `openai-whisper` (torch + CUDA). Point to its Python with `WHISPER_PYTHON`,
  e.g. `export WHISPER_PYTHON=~/.local/share/pipx/venvs/openai-whisper/bin/python`.
- Packages injected there: `stable-ts`, `demucs`
  (install with `pipx inject openai-whisper <package>`; that venv **has no `pip`**).
- whisper models in `~/.cache/whisper/`: `medium.pt`, `large-v3`.
- `demucs` fails to **save** with `torchaudio.save` (it lacks `torchcodec`) →
  use the demucs API and save with the standard `wave` module (see step 2).
- The GPU is sometimes busy (~9 GB from a graphics process, not compute) → for short
  stretches, force CPU with `CUDA_VISIBLE_DEVICES=""`.

## Step 0 — Confirm there is a voice (aggressive transcription)

Cut the doubtful stretch and transcribe with the **thresholds disabled** that make whisper
ignore faint vocals. If text appears where nothing came out before, there is voice to recover.

```bash
VPY="$WHISPER_PYTHON"        # venv with openai-whisper + stable-ts + demucs
FLAC="$MUSIC_DIR/05.my-song.flac"
ffmpeg -v error -ss 138 -t 34 -i "$FLAC" -ac 1 -ar 16000 /tmp/seg.wav -y   # 2:18 + 34s
CUDA_VISIBLE_DEVICES="" "$VPY" -c "
import whisper, warnings; warnings.filterwarnings('ignore')
m=whisper.load_model('large-v3', device='cpu')
r=m.transcribe('/tmp/seg.wav', language='ja', fp16=False,
    no_speech_threshold=1.0, logprob_threshold=-10.0, compression_ratio_threshold=10.0,
    condition_on_previous_text=False, temperature=0.0)
for s in r['segments']: print(s['start'], s['text'].strip())
"
```

## Step 1 — Isolate the vocals (demucs)

Extract the stretch in **44.1 kHz stereo** (demucs separates better with good quality) with
some margin around it.

```bash
ffmpeg -v error -ss 135 -t 37 -i "$FLAC" -ar 44100 -ac 2 /tmp/seg_hq.wav -y
```

## Step 2 — Separate with the demucs API and save with `wave`

(Avoids the `torchcodec` bug; requires neither `soundfile` nor `scipy`.)

```bash
CUDA_VISIBLE_DEVICES="" "$VPY" - <<'PY'
import wave, numpy as np, torch
from demucs.pretrained import get_model
from demucs.apply import apply_model
w = wave.open('/tmp/seg_hq.wav','rb')
n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
a = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float32)/32768.0
w.close()
x = torch.tensor(a.T)                       # (2,n)
m = get_model('htdemucs'); m.cpu().eval()
mean, std = x.mean(), x.std()
with torch.no_grad():
    out = apply_model(m, ((x-mean)/std)[None], device='cpu', progress=False)[0]
out = out*std + mean
voc = np.clip(out[m.sources.index('vocals')].numpy().T, -1, 1)
o = wave.open('/tmp/vocals.wav','wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
o.writeframes((voc*32767).astype(np.int16).tobytes()); o.close()
print('vocals ->/tmp/vocals.wav', sr)
PY
```

## Step 3 — Transcribe the isolated vocals (reliable timestamps)

```bash
CUDA_VISIBLE_DEVICES="" "$VPY" -c "
import whisper, warnings; warnings.filterwarnings('ignore')
m=whisper.load_model('large-v3', device='cpu')
r=m.transcribe('/tmp/vocals.wav', language='ja', word_timestamps=True, fp16=False,
    no_speech_threshold=0.6, condition_on_previous_text=False, temperature=0.0)
off=135  # seconds of the cut's -ss, to get back to the song's real time
for s in r['segments']:
    t=off+s['start']; e=off+s['end']
    print(f'{int(t//60)}:{t%60:05.2f} -> {int(e//60)}:{e%60:05.2f}  {s[\"text\"].strip()}')
"
```

On the clean vocals, whisper gets the text and times right. Even so, **review by hand**: under
music it can swallow particles (typical: the leading `不` of `不完全` → `完全`); fix by
context and, when in doubt, validate by listening.

## Step 4 — Insert into the project

1. Reconstruct the clean Japanese, generate **romaji + Spanish translation**.
2. Insert the lines in their place (chronological order) in **both** files:
   - `lyrics-timed.ass`: only the `Kanji` lines (with their times).
   - `lyrics-fullbackup.ass`: the `Kanji`/`Romaji`/`Spanish` triplet for each line.
   The merge matches Kanji **by sequential order**, so the number and order of Kanji lines
   must match in both (an extra empty Kanji line is cleaned up by `rebuild.sh`).
3. `./rebuild.sh "<folder>"` to merge, add the outro and render.
