#!/usr/bin/env python3
"""
Forced alignment de las líneas Kanji de un .ass contra el audio, usando stable-ts.
Toma el TEXTO como verdad (no deja que whisper decida qué se canta) y solo
recalcula los tiempos start/end de cada línea Kanji en orden secuencial.

Las líneas Romaji/Spanish no se tocan aquí: el merge-trilingual.py les copia
después los tiempos de su Kanji.

Uso:
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

    # Índices y texto de las líneas Kanji, en orden
    kanji = []  # (line_idx, text)
    for idx, ln in enumerate(lines):
        if not ln.startswith("Dialogue:"):
            continue
        parts = ln.split(",", 9)
        if len(parts) >= 10 and parts[3].strip() == "Kanji" and parts[9].strip():
            kanji.append((idx, parts[9].strip()))

    if not kanji:
        print("⚠️  No hay líneas Kanji con texto.")
        return

    text = "\n".join(t for _, t in kanji)

    import stable_whisper
    print(f"→ Cargando modelo whisper '{model_name}'...")
    model = stable_whisper.load_model(model_name)
    print(f"→ Alineando {len(kanji)} líneas contra {audio_path.name}...")
    result = model.align(
        str(audio_path),
        text,
        language="ja",
        original_split=True,   # respeta los \n como límites de segmento
    )

    segs = result.segments
    if len(segs) != len(kanji):
        print(f"⚠️  Segmentos alineados ({len(segs)}) != líneas Kanji ({len(kanji)}).")
        print("    Se aplican en orden los que coincidan; revisa el resultado.")

    n = min(len(segs), len(kanji))
    for k in range(n):
        idx, _ = kanji[k]
        parts = lines[idx].split(",", 9)
        parts[1] = secs_to_ass_time(segs[k].start)
        parts[2] = secs_to_ass_time(segs[k].end)
        lines[idx] = ",".join(parts)

    output_path.write_text("".join(lines), encoding="utf-8")
    print(f"✓ {n} líneas re-sincronizadas por forced alignment.")
    print(f"  Escrito: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    model = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_MODEL
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), model)
