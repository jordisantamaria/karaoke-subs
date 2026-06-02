#!/bin/bash
# Batch-transcribes all tracks with Whisper. JSON output in each folder.
# Walks the "<NN>-*" track folders present in the script's directory and looks for
# their corresponding FLAC in MUSIC_DIR (named "<NN>.*.flac"). Skips the ones that
# already have a JSON.
#
# Variables:
#   MUSIC_DIR      folder with the source FLAC files (required)
#   WHISPER_MODEL  whisper model (default: medium)
#   WHISPER_LANG   language (default: ja)
#
# Usage: MUSIC_DIR="/path/to/album" ./whisper-batch.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MUSIC_DIR="${MUSIC_DIR:?define MUSIC_DIR (folder with the FLAC files named NN.*.flac)}"
WHISPER_MODEL="${WHISPER_MODEL:-medium}"
WHISPER_LANG="${WHISPER_LANG:-ja}"

shopt -s nullglob
for dir in [0-9][0-9]-*/; do
  dir="${dir%/}"
  n="${dir%%-*}"
  flac=$(ls "${MUSIC_DIR}/${n}."*.flac 2>/dev/null | head -1)
  if [ -z "$flac" ]; then
    echo "[$n] ✗ no FLAC found, skip"
    continue
  fi
  json_glob=$(ls "${dir}/${n}."*.json 2>/dev/null | head -1)
  if [ -n "$json_glob" ]; then
    echo "[$n] ✓ JSON already exists, skip"
    continue
  fi
  echo "[$n] → transcribing: $flac"
  whisper "$flac" --model "$WHISPER_MODEL" --language "$WHISPER_LANG" --word_timestamps True \
    --output_format json --output_dir "$dir" 2>&1 | tail -1
  echo "[$n] ✓ done"
done

echo "=== ALL DONE ==="
