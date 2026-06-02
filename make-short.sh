#!/bin/bash
# Generates a short MP4 (H.264 + AAC) ready for X/Twitter from the full webm.
# Usage:
#   ./make-short.sh <track-directory> <start_ts> <duration_sec> [output_name]
# Examples:
#   ./make-short.sh 01-my-song 00:00:58 30                # chorus 1, 30s
#   ./make-short.sh 01-my-song 00:02:33 22 final-chorus   # final chorus

set -e

if [ -z "$3" ]; then
    echo "Usage: $0 <track-directory> <start_ts H:MM:SS> <duration_sec> [output_name]"
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
    echo "Error: $INPUT does not exist (run rebuild.sh first)"
    exit 1
fi

echo "→ Cutting $START + ${DUR}s from $INPUT"
ffmpeg -ss "$START" -i "$INPUT" -t "$DUR" \
  -c:v libopenh264 -b:v 4M -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -y "$OUTPUT" 2>&1 | tail -1

echo ""
echo "✓ Done: $SCRIPT_DIR/$TRACK_DIR/$OUTPUT"
ls -lh "$OUTPUT"
