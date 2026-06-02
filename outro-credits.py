#!/usr/bin/env python3
"""
Places the song title + the artist name in the video OUTRO, in the final gap
without lyrics, using the Title/Credits styles already defined in the .ass.
Idempotent: first deletes any existing Title/Credits line and then re-inserts
the outro ones.

If there is not enough gap at the end (>= MIN_GAP s after the last lyric), it adds
nothing and warns.

The artist name is taken from the KARAOKE_ARTIST environment variable.

Usage:
    KARAOKE_ARTIST="Artist" python outro-credits.py <final.ass> <title> <audio_duration_sec>
"""

import os
import sys
from pathlib import Path

ARTIST = os.environ.get("KARAOKE_ARTIST", "")
MIN_GAP = 6.0       # minimum gap at the end to fit the outro
WINDOW = 9.0        # how long the credits are shown
TAIL_MARGIN = 0.5   # breathing room before the audio ends
LEAD_MARGIN = 3.0   # minimum breathing room after the last lyric before the credits


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

    # 1. Remove previous Title/Credits and compute the end of the last lyric
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
        print(f"⚠️  Final gap {gap:.1f}s < {MIN_GAP}s: no outro added (credits skipped).")
        return

    end = audio_dur - TAIL_MARGIN
    start = max(last_end + LEAD_MARGIN, end - WINDOW)

    # ensure a line terminator on the last line
    if kept and not kept[-1].endswith("\n"):
        kept[-1] += "\n"

    s, e = secs_to_ass_time(start), secs_to_ass_time(end)
    kept.append(f"Dialogue: 0,{s},{e},Title,,0,0,0,,{title}\n")
    kept.append(f"Dialogue: 0,{s},{e},Credits,,0,0,0,,{ARTIST}\n")

    final_path.write_text("".join(kept), encoding="utf-8")
    print(f"✓ Outro added: «{title}» / {ARTIST}  ({s} → {e}, gap {gap:.1f}s)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]))
