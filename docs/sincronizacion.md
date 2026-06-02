# Sincronización de lyrics — método recomendado

Cómo conseguir timing preciso de una canción entera para el karaoke trilingüe.

## Método recomendado: voz aislada + transcripción libre + mapeo

**El que funciona en general** (incluido canciones repetitivas). Pasos (automatizado en
`auto-sync.sh`):

1. **Aislar la voz** de toda la canción con demucs (`isolate-vocals.py`) → quita el
   instrumental, así los interludios son silencio real.
2. **Transcripción libre** de la voz limpia con whisper large-v3 + word timestamps.
   whisper elige texto **y** tiempo a la vez de forma coherente; al ir libre no se
   descarrila con repeticiones (a diferencia del forced alignment).
3. **Mapear** esos tiempos a nuestro texto oficial alineando las dos secuencias de
   caracteres con `difflib` (`sync-from-vocals.py`). Como ambas van en orden
   cronológico, las frases repetidas (`HAPPYBIRTHDAY!`…) se emparejan por posición.
4. Limpieza integrada: recorta solapamientos y capa la última línea (que whisper
   suele inflar con su alucinación de cierre tipo `ご視聴ありがとうございました`).

```bash
export MUSIC_DIR="/ruta/al/album"        # FLAC nombrados NN.*.flac
export WHISPER_PYTHON=~/.local/share/pipx/venvs/openai-whisper/bin/python
./auto-sync.sh "06-mi-cancion"   # sync (no renderiza)
./rebuild.sh   "06-mi-cancion"   # close-gaps + merge + outro + render
```

Requiere un venv con `openai-whisper` + `stable-ts` + `demucs`, y el modelo
`large-v3` en `~/.cache/whisper/`. Si la GPU está ocupada, todo corre en CPU con
`CUDA_VISIBLE_DEVICES=""` (demucs ~70s, transcripción ~par de min).

## Forced alignment (`align-lyrics.py`) — uso limitado

`stable_whisper.align()` fuerza el texto dado y solo decide tiempos. Funciona en
canciones con **letra variada**, pero:
- Se **descarrila con repeticiones** (visto: drift de -50/-70s) — y aislar la voz
  NO lo arregla, porque el problema es la ambigüedad de las repeticiones, no el ruido.
- En interludios instrumentales largos "consume" texto de más (la música no es
  silencio para el detector).

Por eso se prefiere el método de transcripción libre de arriba. El forced alignment
queda como herramienta secundaria.

## Letra que no está en la oficial (recitados/coros enterrados)

Ver `extraer-voz-sin-letra.md`.
