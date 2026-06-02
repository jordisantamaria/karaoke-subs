# Lyrics synchronization — recommended method

How to get precise timing for an entire song for the trilingual karaoke.

## Recommended method: isolated vocals + free transcription + mapping

**The one that works in general** (including repetitive songs). Steps (automated in
`auto-sync.sh`):

1. **Isolate the vocals** of the whole song with demucs (`isolate-vocals.py`) → removes the
   instrumental, so the interludes become real silence.
2. **Free transcription** of the clean vocals with whisper large-v3 + word timestamps.
   whisper picks text **and** time at once in a coherent way; running free, it does not
   derail on repetitions (unlike forced alignment).
3. **Map** those times onto our official text by aligning the two character sequences
   with `difflib` (`sync-from-vocals.py`). Since both go in chronological order, the
   repeated phrases (`HAPPYBIRTHDAY!`…) are matched by position.
4. Built-in cleanup: trims overlaps and caps the last line (which whisper tends to
   inflate with its closing hallucination like `ご視聴ありがとうございました`).

```bash
export MUSIC_DIR="/path/to/album"        # FLAC named NN.*.flac
export WHISPER_PYTHON=~/.local/share/pipx/venvs/openai-whisper/bin/python
./auto-sync.sh "06-my-song"   # sync (does not render)
./rebuild.sh   "06-my-song"   # close-gaps + merge + outro + render
```

Requires a venv with `openai-whisper` + `stable-ts` + `demucs`, and the `large-v3`
model in `~/.cache/whisper/`. If the GPU is busy, everything runs on CPU with
`CUDA_VISIBLE_DEVICES=""` (demucs ~70s, transcription ~a couple of min).

## Forced alignment (`align-lyrics.py`) — limited use

`stable_whisper.align()` forces the given text and only decides the times. It works on
songs with **varied lyrics**, but:
- It **derails on repetitions** (seen: drift of -50/-70s) — and isolating the vocals does
  NOT fix it, because the problem is the ambiguity of the repetitions, not the noise.
- In long instrumental interludes it "consumes" extra text (music is not silence to
  the detector).

That's why the free-transcription method above is preferred. Forced alignment stays as
a secondary tool.

## Lyrics not in the official text (spoken parts / buried backing vocals)

See `extracting-vocals-without-lyrics.md`.
