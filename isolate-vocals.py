#!/usr/bin/env python3
"""
Aísla la pista vocal de un audio con demucs (htdemucs) y la guarda como WAV.
Usa la API de demucs y guarda con el módulo `wave` estándar (evita el bug de
torchaudio.save que exige torchcodec). Pensado para correr en CPU.

Uso:
    python isolate-vocals.py <audio_in> <vocals_out.wav>
"""

import sys, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
import torch
from demucs.pretrained import get_model
from demucs.apply import apply_model


def load_wav_44k_stereo(path: Path) -> tuple[np.ndarray, int]:
    """Decodifica cualquier audio a wav 44.1k estéreo int16 vía ffmpeg y lo lee."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ar", "44100", "-ac", "2", "-y", tmp_path],
        check=True,
    )
    w = wave.open(tmp_path, "rb")
    n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float32) / 32768.0
    w.close()
    Path(tmp_path).unlink(missing_ok=True)
    return a, sr


def main(audio_in: Path, vocals_out: Path):
    a, sr = load_wav_44k_stereo(audio_in)
    x = torch.tensor(a.T)  # (2, n)
    print(f"→ Separando voz con htdemucs ({a.shape[0]/sr:.0f}s de audio, CPU)...")
    m = get_model("htdemucs")
    m.cpu().eval()
    mean, std = x.mean(), x.std()
    with torch.no_grad():
        out = apply_model(m, ((x - mean) / std)[None], device="cpu", progress=True)[0]
    out = out * std + mean
    voc = np.clip(out[m.sources.index("vocals")].numpy().T, -1, 1)
    o = wave.open(str(vocals_out), "wb")
    o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((voc * 32767).astype(np.int16).tobytes())
    o.close()
    print(f"✓ Voz aislada -> {vocals_out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
