#!/bin/bash
# Transcribe en batch todas las pistas con Whisper. Output JSON en cada carpeta.
# Recorre las carpetas de pista "<NN>-*" presentes en el directorio del script y
# busca su FLAC correspondiente en MUSIC_DIR (nombrado "<NN>.*.flac"). Salta las
# que ya tengan JSON.
#
# Variables:
#   MUSIC_DIR      carpeta con los FLAC fuente (obligatoria)
#   WHISPER_MODEL  modelo de whisper (default: medium)
#   WHISPER_LANG   idioma (default: ja)
#
# Uso: MUSIC_DIR="/ruta/al/album" ./whisper-batch.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MUSIC_DIR="${MUSIC_DIR:?define MUSIC_DIR (carpeta con los FLAC nombrados NN.*.flac)}"
WHISPER_MODEL="${WHISPER_MODEL:-medium}"
WHISPER_LANG="${WHISPER_LANG:-ja}"

shopt -s nullglob
for dir in [0-9][0-9]-*/; do
  dir="${dir%/}"
  n="${dir%%-*}"
  flac=$(ls "${MUSIC_DIR}/${n}."*.flac 2>/dev/null | head -1)
  if [ -z "$flac" ]; then
    echo "[$n] ✗ no FLAC encontrado, skip"
    continue
  fi
  json_glob=$(ls "${dir}/${n}."*.json 2>/dev/null | head -1)
  if [ -n "$json_glob" ]; then
    echo "[$n] ✓ ya existe JSON, skip"
    continue
  fi
  echo "[$n] → transcribiendo: $flac"
  whisper "$flac" --model "$WHISPER_MODEL" --language "$WHISPER_LANG" --word_timestamps True \
    --output_format json --output_dir "$dir" 2>&1 | tail -1
  echo "[$n] ✓ done"
done

echo "=== TODO COMPLETADO ==="
