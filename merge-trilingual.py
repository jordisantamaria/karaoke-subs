#!/usr/bin/env python3
"""
Combina el .ass timed (solo Kanji con timings reales) con el fullbackup .ass
(Kanji + Romaji + Spanish con timings viejos) generando un .ass final con
las 3 capas y los timings nuevos.

IMPORTANTE: empareja por ORDEN SECUENCIAL, no por texto, para soportar
líneas Kanji con texto repetido (estribillos, etc.).

Uso:
    python merge-trilingual.py <timed.ass> <fullbackup.ass> <output.ass>
"""

import sys
from pathlib import Path


def parse_dialogues(lines):
    result = []
    for idx, line in enumerate(lines):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        result.append({
            "idx": idx,
            "parts": parts,
            "text": parts[9].strip(),
            "style": parts[3].strip(),
            "start": parts[1],
            "end": parts[2],
        })
    return result


def main(timed_path: Path, full_path: Path, output_path: Path):
    with timed_path.open("r", encoding="utf-8") as f:
        timed_lines = f.readlines()
    with full_path.open("r", encoding="utf-8") as f:
        full_lines = f.readlines()

    timed_dialogues = parse_dialogues(timed_lines)
    full_dialogues = parse_dialogues(full_lines)

    # Listas de Kanji en orden secuencial
    timed_kanji = [d for d in timed_dialogues if d["style"] == "Kanji"]
    full_kanji_positions = [i for i, d in enumerate(full_dialogues) if d["style"] == "Kanji"]

    if len(timed_kanji) != len(full_kanji_positions):
        print(f"⚠️  Mismatch: timed tiene {len(timed_kanji)} líneas Kanji, full tiene {len(full_kanji_positions)}")
        print("    El merge va a aparear las primeras N en orden, las extras quedan sin tocar.")

    output = full_lines.copy()
    updated = 0
    n = min(len(timed_kanji), len(full_kanji_positions))

    for k in range(n):
        new_start = timed_kanji[k]["start"]
        new_end = timed_kanji[k]["end"]

        # Aplica a la línea Kanji + las 2 siguientes (Romaji + Spanish) si las hay en el triplet
        full_kanji_pos = full_kanji_positions[k]
        for offset in range(3):
            j = full_kanji_pos + offset
            if j >= len(full_dialogues):
                break
            target = full_dialogues[j]
            if target["style"] not in ("Kanji", "Romaji", "Spanish"):
                break
            parts = target["parts"].copy()
            parts[1] = new_start
            parts[2] = new_end
            output[target["idx"]] = ",".join(parts)
            updated += 1

    with output_path.open("w", encoding="utf-8") as f:
        f.writelines(output)

    print(f"✓ {updated} líneas con timing actualizado ({n} triplets emparejados por orden).")
    print(f"  Escrito: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
