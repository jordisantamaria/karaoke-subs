#!/usr/bin/env python3
r"""
Exporta una capa (Style) de un .ass a .srt para subir como subtítulos a YouTube.
Excluye Title/Credits (no son lyrics). Limpia tags {\...}.

Uso:
    python ass-to-srt.py <input.ass> <Style> <output.srt>
Ej:
    python ass-to-srt.py 01-my-song/lyrics-final.ass Kanji 01-my-song/01.ja.srt
"""
import sys, re
from pathlib import Path

def ass_to_srt_time(t: str) -> str:
    h, m, s = t.split(":")
    sec = float(s)
    ms = round((sec - int(sec)) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"

def main(inp: Path, style: str, out: Path):
    cues = []
    for ln in inp.read_text(encoding="utf-8").splitlines():
        if not ln.startswith("Dialogue:"):
            continue
        parts = ln.split(",", 9)
        if len(parts) < 10:
            continue
        st = parts[3].strip()
        if st != style:
            continue
        start, end = parts[1].strip(), parts[2].strip()
        text = re.sub(r"\{[^}]*\}", "", parts[9]).strip()
        text = text.replace("\\N", "\n")
        if not text:
            continue
        cues.append((start, end, text))
    lines = []
    for i, (s, e, txt) in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{ass_to_srt_time(s)} --> {ass_to_srt_time(e)}")
        lines.append(txt)
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ {out}  ({len(cues)} cues)")

if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
