#!/usr/bin/env python3
"""
Combines the timed .ass (Kanji only with real timings) with the fullbackup .ass
(Kanji + Romaji + Spanish with old timings), producing a final .ass with the
3 layers and the new timings.

IMPORTANT: matches by SEQUENTIAL ORDER, not by text, to support Kanji lines
with repeated text (choruses, etc.).

Usage:
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

    # Lists of Kanji in sequential order
    timed_kanji = [d for d in timed_dialogues if d["style"] == "Kanji"]
    full_kanji_positions = [i for i, d in enumerate(full_dialogues) if d["style"] == "Kanji"]

    if len(timed_kanji) != len(full_kanji_positions):
        print(f"⚠️  Mismatch: timed has {len(timed_kanji)} Kanji lines, full has {len(full_kanji_positions)}")
        print("    The merge will pair the first N in order; the extras are left untouched.")

    output = full_lines.copy()
    updated = 0
    n = min(len(timed_kanji), len(full_kanji_positions))

    for k in range(n):
        new_start = timed_kanji[k]["start"]
        new_end = timed_kanji[k]["end"]

        # Apply to the Kanji line + the next 2 (Romaji + Spanish) if present in the triplet
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

    print(f"✓ {updated} lines with updated timing ({n} triplets matched by order).")
    print(f"  Written: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
