#!/usr/bin/env python3
"""
Post-procesado: ajusta end-times de líneas Kanji en .ass:
- end = min(next_start - 0.1, start + max_duration)
- Si una línea está fuera de orden (start menor que el anterior), interpola.

Uso:
    python fix-ends.py <input.ass> <output.ass> [max_duration_sec]
"""

import sys
from pathlib import Path


def ass_time_to_secs(t: str) -> float:
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def secs_to_ass_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(input_path: Path, output_path: Path, max_dur: float = 8.0):
    with input_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    kanji_data = []  # list of (line_idx, start_s, end_s)
    for idx, line in enumerate(lines):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 5 or parts[3].strip() != "Kanji":
            continue
        kanji_data.append([idx, ass_time_to_secs(parts[1]), ass_time_to_secs(parts[2])])

    # Step 1: fix out-of-order starts (interpolate)
    for i in range(1, len(kanji_data)):
        if kanji_data[i][1] < kanji_data[i - 1][1]:
            prev = kanji_data[i - 1][1]
            # Find next valid line
            next_valid = None
            for j in range(i + 1, len(kanji_data)):
                if kanji_data[j][1] > prev:
                    next_valid = kanji_data[j][1]
                    break
            if next_valid:
                kanji_data[i][1] = prev + (next_valid - prev) / 2
                kanji_data[i][2] = kanji_data[i][1] + 3
                print(f"  ⚠️  Interpolado start de línea {i}: {kanji_data[i][1]:.2f}s")

    # Step 2: adjust end times with cap
    for i in range(len(kanji_data)):
        idx, start_s, end_s = kanji_data[i]
        if i + 1 < len(kanji_data):
            next_start = kanji_data[i + 1][1]
            new_end = min(next_start - 0.1, start_s + max_dur)
        else:
            new_end = start_s + max_dur
        new_end = max(new_end, start_s + 0.5)
        kanji_data[i][2] = new_end

        parts = lines[idx].split(",", 9)
        parts[1] = secs_to_ass_time(start_s)
        parts[2] = secs_to_ass_time(new_end)
        lines[idx] = ",".join(parts)

    with output_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✓ {len(kanji_data)} líneas ajustadas. Max duración por línea: {max_dur}s")
    print(f"  Escrito: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    max_dur = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    main(Path(sys.argv[1]), Path(sys.argv[2]), max_dur)
