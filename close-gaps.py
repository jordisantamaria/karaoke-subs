#!/usr/bin/env python3
"""
Closes micro handoff-gaps between consecutive Kanji lines: if the gap between the
end of one line and the start of the next is <= threshold, moves the START of the
next line up to the end of the current one (does NOT extend the previous line, so
its sync is not shifted). Large gaps (real pauses/interludes) are left untouched.

Usage:
    python close-gaps.py <input.ass> <output.ass> [threshold_sec]
"""

import sys
from pathlib import Path

DEFAULT_THRESHOLD = 0.3


def ass_time_to_secs(t: str) -> float:
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def secs_to_ass_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(input_path: Path, output_path: Path, threshold: float = DEFAULT_THRESHOLD):
    with input_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    kanji = []  # [line_idx, start_s, end_s]
    for idx, line in enumerate(lines):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 5 or parts[3].strip() != "Kanji":
            continue
        kanji.append([idx, ass_time_to_secs(parts[1]), ass_time_to_secs(parts[2])])

    closed = 0
    for i in range(len(kanji) - 1):
        cur_end = kanji[i][2]
        next_start = kanji[i + 1][1]
        gap = next_start - cur_end
        if 0 < gap <= threshold:
            idx = kanji[i + 1][0]
            parts = lines[idx].split(",", 9)
            parts[1] = secs_to_ass_time(cur_end)
            lines[idx] = ",".join(parts)
            closed += 1

    with output_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✓ {closed} micro-gaps closed (threshold {threshold}s). Rest untouched.")
    print(f"  Written: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_THRESHOLD
    main(Path(sys.argv[1]), Path(sys.argv[2]), thr)
