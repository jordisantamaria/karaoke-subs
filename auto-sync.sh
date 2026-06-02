#!/bin/bash
# Pipeline automático de re-sincronización por VOZ AISLADA para una pista:
#   1. backup del timed
#   2. quita Title/Credits (el outro los recoloca al final en rebuild.sh)
#   3. aísla la voz con demucs
#   4. transcripción libre de la voz + mapeo al texto oficial (sync-from-vocals.py)
# NO renderiza; correr rebuild.sh después.
#
# Uso: ./auto-sync.sh "<carpeta-pista>"
set -e

DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
[ -d "$DIR" ] || { echo "no existe $DIR"; exit 1; }

# MUSIC_DIR: carpeta con los audios fuente, nombrados "<NN>.*.flac" (ej. 01.cancion.flac).
# WHISPER_PYTHON: intérprete del venv con openai-whisper + stable-ts + demucs.
MUSIC_DIR="${MUSIC_DIR:?define MUSIC_DIR (carpeta con los FLAC nombrados NN.*.flac)}"
WHISPER_PYTHON="${WHISPER_PYTHON:-python3}"

TRACK_NUM=$(echo "$DIR" | cut -d'-' -f1)
FLAC=$(ls "${MUSIC_DIR}/${TRACK_NUM}."*.flac 2>/dev/null | head -1)
[ -n "$FLAC" ] || { echo "no FLAC para $TRACK_NUM"; exit 1; }
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
  | grep -aE "líneas sincronizadas|Transcripción|Escrito"
echo "=== auto-sync OK: $DIR ==="
