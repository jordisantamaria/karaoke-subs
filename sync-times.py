#!/usr/bin/env python3
"""
Sincroniza los tiempos de Romaji + Spanish con los de Kanji en un archivo .ass.

Asume que las líneas vienen en orden:
    Kanji, Romaji, Spanish, Kanji, Romaji, Spanish, ...

Uso:
    python sync-times.py <ruta-al-lyrics.ass>

Ejemplo:
    python sync-times.py 01-my-song/lyrics.ass
"""

import sys
from pathlib import Path


def sync_ass_times(ass_path: Path) -> None:
    with ass_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    output = []
    last_kanji_times = None
    synced_count = 0

    for line in lines:
        if not line.startswith("Dialogue:"):
            output.append(line)
            continue

        parts = line.split(",", 9)
        if len(parts) < 5:
            output.append(line)
            continue

        style = parts[3].strip()
        start = parts[1]
        end = parts[2]

        if style == "Kanji":
            last_kanji_times = (start, end)
            output.append(line)
        elif style in ("Romaji", "Spanish") and last_kanji_times:
            parts[1] = last_kanji_times[0]
            parts[2] = last_kanji_times[1]
            output.append(",".join(parts))
            synced_count += 1
        else:
            output.append(line)

    with ass_path.open("w", encoding="utf-8") as f:
        f.writelines(output)

    print(f"✓ Sincronizadas {synced_count} líneas Romaji/Spanish con sus Kanji.")
    print(f"  Archivo: {ass_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: no existe {path}")
        sys.exit(1)

    sync_ass_times(path)
