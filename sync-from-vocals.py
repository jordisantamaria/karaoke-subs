#!/usr/bin/env python3
"""
Re-sincroniza las líneas Kanji de un .ass usando una TRANSCRIPCIÓN LIBRE de la voz
aislada (no forced alignment). whisper transcribe libre la voz limpia (texto+tiempo
coherentes, sin descarrilar con repeticiones), y luego se mapean esos tiempos al
texto oficial alineando ambas secuencias de caracteres con difflib (las dos van en
orden cronológico, así las repeticiones se emparejan por posición).

Uso:
    python sync-from-vocals.py <input.ass> <vocals.wav> <output.ass> [model]
"""

import sys, difflib, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
DEFAULT_MODEL = "large-v3"


def ass_time(secs: float) -> str:
    secs = max(0.0, secs)
    h = int(secs // 3600); m = int((secs % 3600) // 60); s = secs % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(input_path: Path, vocals: Path, output_path: Path, model_name: str):
    lines = input_path.read_text(encoding="utf-8").splitlines(keepends=True)
    # líneas Kanji oficiales (idx en archivo, texto)
    kanji = []
    for i, ln in enumerate(lines):
        if ln.startswith("Dialogue:"):
            p = ln.split(",", 9)
            if len(p) >= 10 and p[3].strip() == "Kanji" and p[9].strip():
                kanji.append((i, p[9].strip()))

    import whisper
    print(f"→ Transcripción libre de la voz ('{model_name}', word timestamps)...")
    model = whisper.load_model(model_name, device="cpu")
    res = model.transcribe(str(vocals), language="ja", fp16=False,
                           word_timestamps=True, no_speech_threshold=0.6,
                           condition_on_previous_text=False, temperature=0.0)

    # caracteres oídos con tiempo (interpolado dentro de cada palabra)
    heard = []  # (char, start, end)
    for seg in res["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            if not t:
                continue
            s, e = w["start"], w["end"]
            n = len(t)
            for k, ch in enumerate(t):
                heard.append((ch, s + (e - s) * k / n, s + (e - s) * (k + 1) / n))
    heard_str = "".join(c for c, _, _ in heard)

    # caracteres oficiales con línea de origen
    off = []  # (char, kanji_index)
    for ki, (_, txt) in enumerate(kanji):
        for ch in txt:
            off.append((ch, ki))
    off_str = "".join(c for c, _ in off)

    # alinear off_str (a) contra heard_str (b)
    sm = difflib.SequenceMatcher(None, off_str, heard_str, autojunk=False)
    amap = [None] * len(off)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
        else:
            si, sj = i2 - i1, j2 - j1
            for k in range(si):
                amap[i1 + k] = (j1 + int(sj * k / si)) if sj > 0 else min(j1, len(heard) - 1)

    # tiempos por línea
    times = [None] * len(kanji)
    for ki in range(len(kanji)):
        js = [amap[ci] for ci, (_, l) in enumerate(off) if l == ki and amap[ci] is not None]
        js = [j for j in js if 0 <= j < len(heard)]
        if js:
            times[ki] = (min(heard[j][1] for j in js), max(heard[j][2] for j in js))

    # rellenar huecos (líneas no oídas) interpolando entre vecinas, y forzar monotonía
    last = 0.0
    for ki in range(len(kanji)):
        if times[ki] is None:
            # busca siguiente con tiempo
            nxt = next((times[k][0] for k in range(ki + 1, len(kanji)) if times[k]), last + 1.0)
            times[ki] = (last, min(nxt, last + 1.5))
        s, e = times[ki]
        s = max(s, last)
        if e <= s:
            e = s + 0.5
        times[ki] = (s, e)
        last = s

    # limpieza: recortar solapamientos (end no excede el start de la siguiente)
    # y capar la última línea (suele inflarse por alucinación de whisper al final)
    for k in range(len(times) - 1):
        s0, e0 = times[k]; sn = times[k + 1][0]
        if e0 > sn > s0:
            times[k] = (s0, sn)
    if times and times[-1][1] - times[-1][0] > 4:
        times[-1] = (times[-1][0], times[-1][0] + 3.0)

    matched = sum(1 for ki in range(len(kanji))
                  if any(amap[ci] is not None for ci, (_, l) in enumerate(off) if l == ki))
    for ki, (idx, _) in enumerate(kanji):
        p = lines[idx].split(",", 9)
        p[1], p[2] = ass_time(times[ki][0]), ass_time(times[ki][1])
        lines[idx] = ",".join(p)

    output_path.write_text("".join(lines), encoding="utf-8")
    print(f"✓ {len(kanji)} líneas sincronizadas ({matched} con match directo de texto).")
    print(f"  Escrito: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    model = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_MODEL
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), model)
