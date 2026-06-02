#!/bin/bash
# Regenera lyrics-final.ass + render webm para una pista.
# Uso:
#   ./rebuild.sh <directorio-pista>
# Ejemplo:
#   ./rebuild.sh 01-my-song

set -e

if [ -z "$1" ]; then
    echo "Uso: $0 <directorio-pista>"
    exit 1
fi

TRACK_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "$TRACK_DIR" ]; then
    echo "Error: no existe el directorio $TRACK_DIR"
    exit 1
fi

# MUSIC_DIR: carpeta con los FLAC fuente (nombrados NN.*.flac).
# COVER_IMAGE: imagen de fondo del vídeo (default _shared/cover.jpg).
MUSIC_DIR="${MUSIC_DIR:?define MUSIC_DIR (carpeta con los FLAC nombrados NN.*.flac)}"
COVER_IMAGE="${COVER_IMAGE:-$SCRIPT_DIR/_shared/cover.jpg}"

# Detecta el FLAC correspondiente
TRACK_NUM=$(echo "$TRACK_DIR" | cut -d'-' -f1)
FLAC_FILE=$(ls "${MUSIC_DIR}/${TRACK_NUM}."*.flac 2>/dev/null | head -1)

if [ -z "$FLAC_FILE" ]; then
    echo "Error: no se encontró el FLAC para pista $TRACK_NUM"
    exit 1
fi

echo "→ Pista: $TRACK_DIR"
echo "→ FLAC:  $FLAC_FILE"
echo ""

# 1. Limpiar líneas Kanji vacías (por si Aegisub añadió alguna)
python3 -c "
import sys
with open('$TRACK_DIR/lyrics-timed.ass', 'r', encoding='utf-8') as f:
    lines = f.readlines()
out = []
removed = 0
for line in lines:
    if line.startswith('Dialogue:'):
        parts = line.split(',', 9)
        if len(parts) >= 10 and parts[3].strip() == 'Kanji' and not parts[9].strip():
            removed += 1
            continue
    out.append(line)
with open('$TRACK_DIR/lyrics-timed.ass', 'w', encoding='utf-8') as f:
    f.writelines(out)
if removed:
    print(f'  Eliminadas {removed} líneas Kanji vacías')
"

# 1b. Cerrar micro-gaps de handoff (<=0.3s) entre líneas Kanji consecutivas
python3 close-gaps.py "$TRACK_DIR/lyrics-timed.ass" "$TRACK_DIR/lyrics-timed.ass"

# 2. Merge trilingual
python3 merge-trilingual.py "$TRACK_DIR/lyrics-timed.ass" "$TRACK_DIR/lyrics-fullbackup.ass" "$TRACK_DIR/lyrics-final.ass"

# 2b. Título + artista en el outro (hueco final sin lyric)
SONG_TITLE=$(echo "${TRACK_DIR##*/}" | sed 's/^[0-9]*-//')
AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FLAC_FILE")
python3 outro-credits.py "$TRACK_DIR/lyrics-final.ass" "$SONG_TITLE" "$AUDIO_DUR"

# 3. Render webm
echo ""
echo "→ Renderizando webm (puede tardar ~1-2 min)..."
cd "$TRACK_DIR"
ffmpeg -loop 1 -framerate 30 -i "$COVER_IMAGE" \
  -i "$FLAC_FILE" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,subtitles=lyrics-final.ass" \
  -c:v libvpx-vp9 -b:v 3M -row-mt 1 -threads 8 -speed 4 \
  -c:a libopus -b:a 192k -shortest \
  -y "${TRACK_DIR##*/}-karaoke.webm" 2>&1 | tail -1

echo ""
echo "✓ Listo: $SCRIPT_DIR/$TRACK_DIR/${TRACK_DIR##*/}-karaoke.webm"
