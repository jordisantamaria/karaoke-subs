#!/usr/bin/env python3
"""
Coloca el título de la canción + el nombre del artista en el OUTRO del vídeo,
en el hueco final sin lyric, usando los estilos Title/Credits ya definidos en el
.ass. Idempotente: primero borra cualquier línea Title/Credits existente y luego
re-inserta las del outro.

Si no hay hueco suficiente al final (>= MIN_GAP s tras la última lyric), no añade
nada y avisa.

El nombre del artista se toma de la variable de entorno KARAOKE_ARTIST.

Uso:
    KARAOKE_ARTIST="Artista" python outro-credits.py <final.ass> <titulo> <audio_duration_sec>
"""

import os
import sys
from pathlib import Path

ARTIST = os.environ.get("KARAOKE_ARTIST", "")
MIN_GAP = 6.0       # hueco mínimo al final para meter el outro
WINDOW = 9.0        # cuánto tiempo se muestran los créditos
TAIL_MARGIN = 0.5   # respiro antes de que acabe el audio
LEAD_MARGIN = 3.0   # respiro mínimo tras la última lyric antes de los créditos


def ass_time_to_secs(t: str) -> float:
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def secs_to_ass_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(final_path: Path, title: str, audio_dur: float):
    lines = final_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # 1. Quita Title/Credits previos y calcula el fin de la última lyric
    kept, last_end = [], 0.0
    for ln in lines:
        if ln.startswith("Dialogue:"):
            parts = ln.split(",", 9)
            if len(parts) >= 4 and parts[3].strip() in ("Title", "Credits"):
                continue
            if len(parts) >= 3:
                last_end = max(last_end, ass_time_to_secs(parts[2]))
        kept.append(ln)

    gap = audio_dur - last_end
    if gap < MIN_GAP:
        final_path.write_text("".join(kept), encoding="utf-8")
        print(f"⚠️  Hueco final {gap:.1f}s < {MIN_GAP}s: no se añade outro (créditos omitidos).")
        return

    end = audio_dur - TAIL_MARGIN
    start = max(last_end + LEAD_MARGIN, end - WINDOW)

    # asegura terminador de línea en la última
    if kept and not kept[-1].endswith("\n"):
        kept[-1] += "\n"

    s, e = secs_to_ass_time(start), secs_to_ass_time(end)
    kept.append(f"Dialogue: 0,{s},{e},Title,,0,0,0,,{title}\n")
    kept.append(f"Dialogue: 0,{s},{e},Credits,,0,0,0,,{ARTIST}\n")

    final_path.write_text("".join(kept), encoding="utf-8")
    print(f"✓ Outro añadido: «{title}» / {ARTIST}  ({s} → {e}, hueco {gap:.1f}s)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]))
