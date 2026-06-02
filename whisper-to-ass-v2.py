#!/usr/bin/env python3
"""
v2: Matches each Kanji line to a subrange of WORDS (not segments) using a
sliding window over the word stream. Better than v1 when Whisper consolidates
multiple lines into a single segment.

Usage:
    python whisper-to-ass-v2.py <whisper.json> <input.ass> <output.ass>
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def normalize(text: str) -> str:
    text = re.sub(r"[「」『』（）()【】\[\]、。，．,\.\!\?！？☆♡♪×!\s]+", "", text)
    return text.lower()


def secs_to_ass_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_word_stream(segments):
    """Returns a list of dicts {char, start, end} character-by-character."""
    stream = []
    for seg in segments:
        for w in seg.get("words", []):
            text = w["word"].strip()
            if not text:
                continue
            ws = w["start"]
            we = w["end"]
            # Spread the time across the characters
            n = len(text)
            if n == 0:
                continue
            per = (we - ws) / n
            for i, ch in enumerate(text):
                if ch.isspace():
                    continue
                stream.append({"char": ch, "start": ws + i * per, "end": ws + (i + 1) * per})
    return stream


def find_best_window(target_norm, stream, start_idx, max_skip=80, max_window_extra=10):
    """
    Searches stream[start_idx..] for the range [i..j] whose concatenation of chars
    best matches target_norm. Returns (best_i, best_j, score).
    """
    L = len(target_norm)
    if L == 0:
        return -1, -1, 0.0

    best_i = -1
    best_j = -1
    best_score = 0.0

    # Try different start positions near start_idx
    for i in range(start_idx, min(start_idx + max_skip, len(stream))):
        # Try different window lengths near L
        for window_len in range(max(1, L - max_window_extra), L + max_window_extra + 1):
            j = i + window_len
            if j > len(stream):
                break
            candidate = "".join(s["char"] for s in stream[i:j])
            score = SequenceMatcher(None, target_norm, normalize(candidate)).ratio()
            if score > best_score:
                best_score = score
                best_i = i
                best_j = j

    return best_i, best_j, best_score


def main(whisper_json_path: Path, input_ass_path: Path, output_ass_path: Path):
    with whisper_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    stream = build_word_stream(segments)
    print(f"Word stream: {len(stream)} chars ({len(segments)} segments)")

    with input_ass_path.open("r", encoding="utf-8") as f:
        ass_lines = f.readlines()

    kanji_dialogues = []
    for idx, line in enumerate(ass_lines):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10 or parts[3].strip() != "Kanji":
            continue
        text = parts[9].strip()
        kanji_dialogues.append({"idx": idx, "text": text, "parts": parts})

    print(f"Kanji lines: {len(kanji_dialogues)}")

    last_pos = 0
    matches = []
    for kd in kanji_dialogues:
        target_norm = normalize(kd["text"])
        i, j, score = find_best_window(target_norm, stream, last_pos)
        if i >= 0 and score > 0.4:
            start = stream[i]["start"]
            end = stream[j - 1]["end"] if j - 1 < len(stream) else stream[-1]["end"]
            matches.append({
                "kanji_idx": kd["idx"], "kanji_text": kd["text"],
                "start": start, "end": end, "score": score,
                "matched": "".join(s["char"] for s in stream[i:j])
            })
            last_pos = j
        else:
            matches.append({
                "kanji_idx": kd["idx"], "kanji_text": kd["text"],
                "start": None, "end": None, "score": score,
                "matched": None
            })

    # Linear interpolation between consecutive matches for unmatched lines
    interpolated = 0
    n = len(matches)
    for i in range(n):
        if matches[i]["start"] is not None:
            continue
        # Find the previous and next match
        prev_i = next_i = None
        for k in range(i - 1, -1, -1):
            if matches[k]["start"] is not None:
                prev_i = k
                break
        for k in range(i + 1, n):
            if matches[k]["start"] is not None:
                next_i = k
                break
        if prev_i is not None and next_i is not None:
            prev_end = matches[prev_i]["end"]
            next_start = matches[next_i]["start"]
            gap = next_start - prev_end
            n_unmatched_between = next_i - prev_i - 1
            slot = gap / max(1, n_unmatched_between + 1)
            offset = i - prev_i
            matches[i]["start"] = prev_end + slot * offset
            matches[i]["end"] = matches[i]["start"] + slot * 0.9
            interpolated += 1
        elif prev_i is not None:
            matches[i]["start"] = matches[prev_i]["end"] + 0.5
            matches[i]["end"] = matches[i]["start"] + 3.0
            interpolated += 1
        elif next_i is not None:
            matches[i]["end"] = matches[next_i]["start"] - 0.5
            matches[i]["start"] = max(0, matches[i]["end"] - 3.0)
            interpolated += 1

    output_lines = ass_lines.copy()
    matched_count = 0
    for m in matches:
        if m["start"] is None:
            continue
        idx = m["kanji_idx"]
        parts = output_lines[idx].split(",", 9)
        parts[1] = secs_to_ass_time(m["start"])
        parts[2] = secs_to_ass_time(m["end"])
        output_lines[idx] = ",".join(parts)
        matched_count += 1

    with output_ass_path.open("w", encoding="utf-8") as f:
        f.writelines(output_lines)

    real_matches = matched_count - interpolated
    print(f"✓ {real_matches}/{len(kanji_dialogues)} matched ({interpolated} interpolated)")
    print(f"  Written: {output_ass_path}")

    print("\n--- Detail ---")
    for m in matches:
        if m["start"] is not None:
            print(f"  [{m['score']:.2f}] {secs_to_ass_time(m['start'])}-{secs_to_ass_time(m['end'])} {m['kanji_text'][:25]:<25} ⇆ {m['matched'][:30]}")
        else:
            print(f"  [NO MATCH {m['score']:.2f}] {m['kanji_text'][:30]}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
