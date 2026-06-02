#!/usr/bin/env python3
"""
Toma un JSON de output de Whisper + un .ass con líneas Kanji (timings provisionales)
y reescribe el .ass con timings reales basados en el matching texto-a-segmento.

Uso:
    python whisper-to-ass.py <whisper.json> <input.ass> <output.ass>

Ejemplo:
    python whisper-to-ass.py 01-my-song/whisper.json 01-my-song/lyrics.ass 01-my-song/lyrics-timed.ass
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def normalize(text: str) -> str:
    """Normaliza texto para comparación: quita puntuación, espacios, símbolos."""
    text = re.sub(r"[「」『』（）()【】\[\]、。，．,\.\!\?！？☆♡♪×!\s]+", "", text)
    return text.lower()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def secs_to_ass_time(secs: float) -> str:
    """Convierte segundos a formato H:MM:SS.CC del .ass"""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def find_best_segment(target: str, segments: list, start_idx: int, window: int = 6) -> tuple[int, float]:
    """Busca el mejor segmento Whisper que matchee `target`, partiendo de start_idx."""
    best_idx = -1
    best_score = 0.0
    end = min(start_idx + window, len(segments))
    for i in range(start_idx, end):
        score = similarity(target, segments[i]["text"])
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx, best_score


def main(whisper_json_path: Path, input_ass_path: Path, output_ass_path: Path):
    with whisper_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    print(f"Whisper devolvió {len(segments)} segmentos.")

    with input_ass_path.open("r", encoding="utf-8") as f:
        ass_lines = f.readlines()

    # Extraer líneas Dialogue con style Kanji
    kanji_dialogues = []
    for idx, line in enumerate(ass_lines):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 5:
            continue
        if parts[3].strip() != "Kanji":
            continue
        text = parts[9].strip() if len(parts) > 9 else ""
        kanji_dialogues.append({"idx": idx, "text": text, "parts": parts})

    print(f"Encontradas {len(kanji_dialogues)} líneas Kanji en el .ass.")

    # Matching secuencial con ventana
    last_seg_idx = 0
    matches = []
    for kd in kanji_dialogues:
        best_idx, best_score = find_best_segment(kd["text"], segments, last_seg_idx)
        if best_idx >= 0 and best_score > 0.3:
            seg = segments[best_idx]
            matches.append({
                "kanji_idx": kd["idx"],
                "kanji_text": kd["text"],
                "seg_text": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
                "score": best_score,
            })
            last_seg_idx = best_idx + 1
        else:
            print(f"⚠️  No match para: {kd['text'][:40]} (mejor score: {best_score:.2f})")
            matches.append({
                "kanji_idx": kd["idx"],
                "kanji_text": kd["text"],
                "seg_text": None,
                "start": None,
                "end": None,
                "score": best_score,
            })

    # Reescribir .ass con nuevos timings
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

    print(f"\n✓ {matched_count}/{len(kanji_dialogues)} líneas Kanji con timing nuevo.")
    print(f"  Escrito: {output_ass_path}")

    # Reporte de matching
    print("\n--- Matching detallado ---")
    for m in matches:
        if m["seg_text"]:
            print(f"  [{m['score']:.2f}] {m['kanji_text'][:30]:<30} ⇆ {m['seg_text'][:40]}")
        else:
            print(f"  [SIN MATCH] {m['kanji_text'][:30]}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
