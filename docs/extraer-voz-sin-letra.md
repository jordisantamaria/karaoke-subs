# Extraer voz cuando NO tenemos letra (recitados / coros enterrados)

Procedimiento para recuperar partes cantadas/habladas que **no están en la letra oficial**
y que whisper, en modo normal, descarta por estar mezcladas bajo el instrumental
(las clasifica como "música", no como voz).

Ejemplo típico: un recitado hablado en un interludio (p.ej. 2:22–2:48) que no
figuraba en la letra oficial del booklet.

## Síntomas

- Hueco sin subtítulo en el vídeo, pero **al escuchar SÍ hay voz**.
- La transcripción normal de whisper no devuelve nada en ese tramo (lo trata como interludio).

## Entorno (ya instalado)

- venv con `openai-whisper` (torch + CUDA). Apunta a su Python con `WHISPER_PYTHON`,
  p.ej. `export WHISPER_PYTHON=~/.local/share/pipx/venvs/openai-whisper/bin/python`.
- Paquetes inyectados ahí: `stable-ts`, `demucs`
  (instalar con `pipx inject openai-whisper <paquete>`; ese venv **no tiene `pip`**).
- Modelos whisper en `~/.cache/whisper/`: `medium.pt`, `large-v3`.
- `demucs` falla al **guardar** con `torchaudio.save` (le falta `torchcodec`) →
  usar la API de demucs y guardar con el módulo `wave` estándar (ver paso 2).
- La GPU a veces está ocupada (~9 GB por proceso gráfico, no compute) → para tramos
  cortos forzar CPU con `CUDA_VISIBLE_DEVICES=""`.

## Paso 0 — Confirmar que hay voz (transcripción agresiva)

Recorta el tramo dudoso y transcribe **desactivando los umbrales** que hacen a whisper
ignorar voz tenue. Si aparece texto donde antes no salía nada, hay voz que recuperar.

```bash
VPY="$WHISPER_PYTHON"        # venv con openai-whisper + stable-ts + demucs
FLAC="$MUSIC_DIR/05.mi-cancion.flac"
ffmpeg -v error -ss 138 -t 34 -i "$FLAC" -ac 1 -ar 16000 /tmp/seg.wav -y   # 2:18 + 34s
CUDA_VISIBLE_DEVICES="" "$VPY" -c "
import whisper, warnings; warnings.filterwarnings('ignore')
m=whisper.load_model('large-v3', device='cpu')
r=m.transcribe('/tmp/seg.wav', language='ja', fp16=False,
    no_speech_threshold=1.0, logprob_threshold=-10.0, compression_ratio_threshold=10.0,
    condition_on_previous_text=False, temperature=0.0)
for s in r['segments']: print(s['start'], s['text'].strip())
"
```

## Paso 1 — Aislar la voz (demucs)

Extrae el tramo en **44.1 kHz estéreo** (demucs separa mejor con buena calidad) con
algo de margen alrededor.

```bash
ffmpeg -v error -ss 135 -t 37 -i "$FLAC" -ar 44100 -ac 2 /tmp/seg_hq.wav -y
```

## Paso 2 — Separar con la API de demucs y guardar con `wave`

(Evita el bug de `torchcodec`; no requiere `soundfile` ni `scipy`.)

```bash
CUDA_VISIBLE_DEVICES="" "$VPY" - <<'PY'
import wave, numpy as np, torch
from demucs.pretrained import get_model
from demucs.apply import apply_model
w = wave.open('/tmp/seg_hq.wav','rb')
n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
a = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float32)/32768.0
w.close()
x = torch.tensor(a.T)                       # (2,n)
m = get_model('htdemucs'); m.cpu().eval()
mean, std = x.mean(), x.std()
with torch.no_grad():
    out = apply_model(m, ((x-mean)/std)[None], device='cpu', progress=False)[0]
out = out*std + mean
voc = np.clip(out[m.sources.index('vocals')].numpy().T, -1, 1)
o = wave.open('/tmp/vocals.wav','wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
o.writeframes((voc*32767).astype(np.int16).tobytes()); o.close()
print('vocals ->/tmp/vocals.wav', sr)
PY
```

## Paso 3 — Transcribir la voz aislada (timestamps fiables)

```bash
CUDA_VISIBLE_DEVICES="" "$VPY" -c "
import whisper, warnings; warnings.filterwarnings('ignore')
m=whisper.load_model('large-v3', device='cpu')
r=m.transcribe('/tmp/vocals.wav', language='ja', word_timestamps=True, fp16=False,
    no_speech_threshold=0.6, condition_on_previous_text=False, temperature=0.0)
off=135  # segundos del -ss del recorte, para volver al tiempo real de la canción
for s in r['segments']:
    t=off+s['start']; e=off+s['end']
    print(f'{int(t//60)}:{t%60:05.2f} -> {int(e//60)}:{e%60:05.2f}  {s[\"text\"].strip()}')
"
```

Sobre la voz limpia, whisper acierta texto y tiempos. Aun así, **revisar a mano**: bajo
música puede comerse partículas (típico: el `不` inicial de `不完全` → `完全`); corregir
por contexto y, si se duda, validar escuchando.

## Paso 4 — Insertar en el proyecto

1. Reconstruir el japonés limpio, generar **romaji + traducción español**.
2. Insertar las líneas en su sitio (orden cronológico) en **ambos** archivos:
   - `lyrics-timed.ass`: solo las líneas `Kanji` (con sus tiempos).
   - `lyrics-fullbackup.ass`: el triplet `Kanji`/`Romaji`/`Spanish` por cada línea.
   El merge empareja Kanji **por orden secuencial**, así que el nº y orden de líneas
   Kanji debe coincidir en los dos (una línea Kanji vacía sobrante la limpia `rebuild.sh`).
3. `./rebuild.sh "<carpeta>"` para mergear, añadir outro y renderizar.
