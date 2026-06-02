# Ejemplo: «DAY×DAY» — muestra de 28s

Fragmento del estribillo (56.5s–84.5s) del tema **「DAY×DAY」** de **鈴音ひとみ**
(Hitonyan), usado como demostración del resultado del toolkit.

> Material publicado con permiso de la artista.

## Contenido

| Archivo | Qué es |
|---|---|
| `preview.mp4` | El resultado: vídeo karaoke trilingüe de 28s (cover + audio + subtítulos quemados). |
| `clip.flac` | El audio fuente del fragmento (input del pipeline). |
| `lyrics-final.md` | La letra trilingüe del tramo (formato fuente, ver README principal). |
| `lyrics-final.ass` | Los subtítulos sincronizados (output, reescalados a 0–28s). |
| `cover.jpg` | Imagen de fondo del vídeo. |

## Reproducir el render

Desde esta carpeta, el mismo comando que usa `rebuild.sh`:

```bash
ffmpeg -loop 1 -framerate 30 -i cover.jpg -i clip.flac \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,subtitles=lyrics-final.ass" \
  -c:v libopenh264 -b:v 4M -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart -shortest \
  -y preview.mp4
```

Necesitas `ffmpeg` y una fuente CJK instalada (`Noto Sans CJK JP`).
