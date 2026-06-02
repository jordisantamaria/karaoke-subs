#!/bin/bash
# Genera un short MP4 (H.264 + AAC) listo para X/Twitter a partir del webm completo.
# Uso:
#   ./make-short.sh <directorio-pista> <start_ts> <duration_sec> [output_name]
# Ejemplos:
#   ./make-short.sh 01-my-song 00:00:58 30                # chorus 1, 30s
#   ./make-short.sh 01-my-song 00:02:33 22 final-chorus   # final chorus

set -e

if [ -z "$3" ]; then
    echo "Uso: $0 <directorio-pista> <start_ts H:MM:SS> <duration_sec> [output_name]"
    exit 1
fi

TRACK_DIR="$1"
START="$2"
DUR="$3"
NAME="${4:-teaser}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/$TRACK_DIR"

INPUT="${TRACK_DIR##*/}-karaoke.webm"
OUTPUT="${TRACK_DIR##*/}-${NAME}.mp4"

if [ ! -f "$INPUT" ]; then
    echo "Error: no existe $INPUT (corre rebuild.sh antes)"
    exit 1
fi

echo "→ Cortando $START + ${DUR}s de $INPUT"
ffmpeg -ss "$START" -i "$INPUT" -t "$DUR" \
  -c:v libopenh264 -b:v 4M -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -y "$OUTPUT" 2>&1 | tail -1

echo ""
echo "✓ Listo: $SCRIPT_DIR/$TRACK_DIR/$OUTPUT"
ls -lh "$OUTPUT"
