# Example: «DAY×DAY» — 28s sample

Chorus fragment (56.5s–84.5s) of the song **「DAY×DAY」** by **鈴音ひとみ**
(Hitonyan), used to demonstrate the toolkit's result.

> Material published with the artist's permission.

## Contents

| File | What it is |
|---|---|
| `preview.mp4` | The result: 28s trilingual karaoke video (cover + audio + burned-in subtitles). |
| `clip.flac` | The source audio of the fragment (pipeline input). |
| `lyrics-final.md` | The trilingual lyrics of the stretch (source format, see the main README). |
| `lyrics-final.ass` | The synced subtitles (output, rescaled to 0–28s). |
| `cover.jpg` | Video background image. |

## Reproduce the render

From this folder, the same command that `rebuild.sh` uses:

```bash
ffmpeg -loop 1 -framerate 30 -i cover.jpg -i clip.flac \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,subtitles=lyrics-final.ass" \
  -c:v libopenh264 -b:v 4M -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart -shortest \
  -y preview.mp4
```

You need `ffmpeg` and a CJK font installed (`Noto Sans CJK JP`).
