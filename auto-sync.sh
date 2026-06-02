#!/bin/bash
# Automatic re-sync pipeline via ISOLATED VOCALS for a track:
#   1. back up the timed file
#   2. remove Title/Credits (the outro re-places them at the end in rebuild.sh)
#   3. isolate the vocals with demucs
#   4. free transcription of the vocals + mapping to the official text (sync-from-vocals.py)
# Does NOT render; run rebuild.sh afterwards.
#
# Usage: ./auto-sync.sh "<track-folder>"
set -e

DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
[ -d "$DIR" ] || { echo "$DIR does not exist"; exit 1; }

# MUSIC_DIR: folder with the source audio files, named "<NN>.*.flac" (e.g. 01.song.flac).
# WHISPER_PYTHON: the venv's interpreter with openai-whisper + stable-ts + demucs.
MUSIC_DIR="${MUSIC_DIR:?define MUSIC_DIR (folder with the FLAC files named NN.*.flac)}"
WHISPER_PYTHON="${WHISPER_PYTHON:-python3}"

TRACK_NUM=$(echo "$DIR" | cut -d'-' -f1)
FLAC=$(ls "${MUSIC_DIR}/${TRACK_NUM}."*.flac 2>/dev/null | head -1)
[ -n "$FLAC" ] || { echo "no FLAC for $TRACK_NUM"; exit 1; }
VPY="$WHISPER_PYTHON"
VOC="/tmp/vocals_${TRACK_NUM}.wav"

echo "=== auto-sync: $DIR ==="
cp "$DIR/lyrics-timed.ass" "$DIR/lyrics-timed.ass.manual"

python3 - "$DIR" <<'PY'
import sys
from pathlib import Path
d = sys.argv[1]
for f in [f"{d}/lyrics-fullbackup.ass", f"{d}/lyrics-timed.ass"]:
    p = Path(f); out = []; rm = 0
    for ln in p.read_text(encoding="utf-8").splitlines(keepends=True):
        if ln.startswith("Dialogue:"):
            pr = ln.split(",", 9)
            if len(pr) >= 4 and pr[3].strip() in ("Title", "Credits"):
                rm += 1; continue
        out.append(ln)
    p.write_text("".join(out), encoding="utf-8")
    print(f"  {f}: -{rm} Title/Credits")
PY

CUDA_VISIBLE_DEVICES="" "$VPY" isolate-vocals.py "$FLAC" "$VOC" 2>&1 \
  | grep -vE "FutureWarning|warnings.warn|UserWarning|weight_norm|torch.nn.utils|^\s+[0-9].*%\|" | tail -2
CUDA_VISIBLE_DEVICES="" "$VPY" sync-from-vocals.py "$DIR/lyrics-timed.ass" "$VOC" "$DIR/lyrics-timed.ass" large-v3 2>&1 \
  | grep -aE "lines synced|Free transcription|Written"
echo "=== auto-sync OK: $DIR ==="
