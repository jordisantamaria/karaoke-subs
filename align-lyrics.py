#!/usr/bin/env python3
"""
Forced alignment of the Kanji lines of an .ass against the audio, using stable-ts.
Takes the TEXT as ground truth (does not let whisper decide what is sung) and only
recomputes the start/end times of each Kanji line in sequential order.

The Romaji/Spanish lines are not touched here: merge-trilingual.py copies the
times from their Kanji afterwards.

Usage:
    python align-lyrics.py <input.ass> <audio> <output.ass> [model]
"""

import sys
from pathlib import Path

DEFAULT_MODEL = "medium"


def secs_to_ass_time(secs: float) -> str:
    secs = max(0.0, secs)
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(input_path: Path, audio_path: Path, output_path: Path, model_name: str):
    lines = input_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Indices and text of the Kanji lines, in order
    kanji = []  # (line_idx, text)
    for idx, ln in enumerate(lines):
        if not ln.startswith("Dialogue:"):
            continue
        parts = ln.split(",", 9)
        if len(parts) >= 10 and parts[3].strip() == "Kanji" and parts[9].strip():
            kanji.append((idx, parts[9].strip()))

    if not kanji:
        print("⚠️  No Kanji lines with text.")
        return

    text = "\n".join(t for _, t in kanji)

    import stable_whisper
    print(f"→ Loading whisper model '{model_name}'...")
    model = stable_whisper.load_model(model_name)
    print(f"→ Aligning {len(kanji)} lines against {audio_path.name}...")
    result = model.align(
        str(audio_path),
        text,
        language="ja",
        original_split=True,   # respect the \n as segment boundaries
    )

    segs = result.segments
    if len(segs) != len(kanji):
        print(f"⚠️  Aligned segments ({len(segs)}) != Kanji lines ({len(kanji)}).")
        print("    The matching ones are applied in order; check the result.")

    n = min(len(segs), len(kanji))
    for k in range(n):
        idx, _ = kanji[k]
        parts = lines[idx].split(",", 9)
        parts[1] = secs_to_ass_time(segs[k].start)
        parts[2] = secs_to_ass_time(segs[k].end)
        lines[idx] = ",".join(parts)

    output_path.write_text("".join(lines), encoding="utf-8")
    print(f"✓ {n} lines re-synced by forced alignment.")
    print(f"  Written: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    model = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_MODEL
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), model)
