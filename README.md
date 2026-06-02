# karaoke-trilingual-subs

Toolkit para generar vídeos de **karaoke trilingüe** (japonés + romaji + traducción)
a partir de un álbum de audio y su letra oficial. Sincroniza el timing automáticamente
aislando la voz con [demucs](https://github.com/adefossez/demucs) y transcribiéndola con
[Whisper](https://github.com/openai/whisper), luego mapea esos tiempos a tu texto oficial
y renderiza un `.webm` con subtítulos `.ass`.

> Pensado para un flujo japonés→romaji→español, pero los estilos y el idioma de
> traducción son configurables.

## Por qué este enfoque

El *forced alignment* clásico se descarrila en canciones con estribillos repetidos y
"consume" texto en los interludios instrumentales. En su lugar:

1. **Aísla la voz** (demucs) → los interludios pasan a ser silencio real.
2. **Transcripción libre** de la voz limpia (Whisper large-v3 + word timestamps):
   Whisper elige texto **y** tiempo de forma coherente, sin descarrilarse con repeticiones.
3. **Mapea** esos tiempos a tu texto oficial alineando ambas secuencias de caracteres
   con `difflib`. Como las dos van en orden cronológico, las frases repetidas se
   emparejan por posición.

Detalle completo en [`docs/sincronizacion.md`](docs/sincronizacion.md).

## Requisitos

- **Python 3.9+**, **ffmpeg/ffprobe**
- Un venv con `openai-whisper` + `stable-ts` + `demucs` (se recomienda pipx):
  ```bash
  pipx install openai-whisper
  pipx inject openai-whisper stable-ts demucs
  ```
- El modelo `large-v3` de Whisper en `~/.cache/whisper/` (se descarga solo al primer uso).
- Fuente CJK instalada para el render (los estilos usan `Noto Sans CJK JP`).

## Configuración (variables de entorno)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `MUSIC_DIR` | sí | Carpeta con los audios fuente, nombrados `<NN>.*.flac` (ej. `01.cancion.flac`). |
| `WHISPER_PYTHON` | recomendada | Python del venv con whisper/stable-ts/demucs. Default `python3`. |
| `KARAOKE_ARTIST` | recomendada | Nombre del artista para el título y los créditos del outro. |
| `COVER_IMAGE` | no | Imagen de fondo del vídeo. Default `_shared/cover.jpg`. |
| `WHISPER_MODEL` | no | Modelo para `whisper-batch.sh`. Default `medium`. |
| `WHISPER_LANG` | no | Idioma. Default `ja`. |

```bash
export MUSIC_DIR="/ruta/al/album"
export WHISPER_PYTHON=~/.local/share/pipx/venvs/openai-whisper/bin/python
export KARAOKE_ARTIST="Mi Artista"
export COVER_IMAGE="$PWD/_shared/cover.jpg"
```

## Estructura de trabajo

Una carpeta por pista, nombrada `<NN>-<slug>` (ej. `01-my-song`). Dentro:

```
01-my-song/
  lyrics-final.md        # tu letra trilingüe (fuente, ver formato abajo)
  lyrics.ass             # generado: solo Kanji (input de sync)
  lyrics-fullbackup.ass  # generado: trilingüe (fuente del merge)
  lyrics-timed.ass       # generado: Kanji con timing sincronizado
  lyrics-final.ass       # generado: trilingüe + outro, listo para render
  01-my-song-karaoke.webm
```

### Formato de `lyrics-final.md`

Secciones con `## [nombre]` y, dentro, un bloque por línea cantada:

````markdown
## [Verse 1]

```
JP:  情報混線社会
RO:  Jouhou konsen shakai
ES:  Sociedad de información saturada
```
````

## Flujo de uso

```bash
# 1. Generar los .ass placeholder desde lyrics-final.md
python gen-ass.py 01-my-song "Título de la canción" 01 211   # 211 = duración en seg

# 2. Sincronizar el timing por voz aislada (demucs + whisper)
./auto-sync.sh 01-my-song

# 3. (opcional) Afinar a mano en Aegisub sobre lyrics-timed.ass

# 4. Merge trilingüe + outro + render del webm
./rebuild.sh 01-my-song

# 5. (opcional) Recortar un teaser para redes
./make-short.sh 01-my-song 00:00:58 30 chorus
```

`whisper-batch.sh` transcribe todas las pistas presentes en batch (paso previo opcional).

## Scripts

| Script | Función |
|---|---|
| `gen-ass.py` | Genera `lyrics.ass` (Kanji) y `lyrics-fullbackup.ass` (trilingüe) desde `lyrics-final.md`. |
| `isolate-vocals.py` | Aísla la voz de un audio con demucs. |
| `sync-from-vocals.py` | Transcribe la voz aislada y mapea los tiempos al texto oficial. |
| `auto-sync.sh` | Orquesta aislar voz + sincronizar (no renderiza). |
| `whisper-to-ass.py` / `whisper-to-ass-v2.py` | Convierte JSON de Whisper a `.ass` con timing. |
| `align-lyrics.py` | Forced alignment (uso secundario, ver docs). |
| `close-gaps.py` | Cierra micro-huecos de handoff entre líneas. |
| `fix-ends.py` / `sync-times.py` | Ajustes de tiempos. |
| `merge-trilingual.py` | Funde el timing Kanji con las capas romaji/traducción. |
| `outro-credits.py` | Inserta título + artista en el hueco final. |
| `rebuild.sh` | Merge + outro + render del `.webm`. |
| `ass-to-srt.py` | Exporta una capa del `.ass` a `.srt`. |
| `make-short.sh` | Recorta un clip MP4 para redes. |

## Ejemplo

En [`examples/01-day-x-day-30s/`](examples/01-day-x-day-30s/) hay una muestra real de
28s del tema «DAY×DAY» de 鈴音ひとみ (publicada con permiso de la artista): el
`preview.mp4` resultante, el `clip.flac` fuente, la letra trilingüe y el `.ass`
sincronizado. Sirve para ver el formato de entrada y el resultado de un vistazo.

## Documentación

- [`docs/sincronizacion.md`](docs/sincronizacion.md) — método de sincronización en detalle.
- [`docs/extraer-voz-sin-letra.md`](docs/extraer-voz-sin-letra.md) — recuperar recitados/coros que no están en la letra oficial.

## Licencia

MIT — ver [`LICENSE`](LICENSE). El toolkit es código propio; el audio, las letras y la
carátula que proceses con él son material de sus respectivos titulares de derechos.
