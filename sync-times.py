#!/usr/bin/env python3
"""
Syncs the times of Romaji + Spanish with those of Kanji in an .ass file.

Assumes the lines come in order:
    Kanji, Romaji, Spanish, Kanji, Romaji, Spanish, ...

Usage:
    python sync-times.py <path-to-lyrics.ass>

Example:
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

    print(f"✓ Synced {synced_count} Romaji/Spanish lines with their Kanji.")
    print(f"  File: {ass_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)

    sync_ass_times(path)
