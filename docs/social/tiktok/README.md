# TikTok-Teaser (Malipin)

Drei 12-Sekunden-Videos im Mali-Pixel-Look, 1080×1920, mit eigenem Chiptune-Sound (150 BPM).

| Datei | Inhalt |
|---|---|
| `video.html` | Animation, Bild für Bild (`?v=1`, `?v=2`, `?v=3`) |
| `sound.py` | Musik + Effekte, selbst erzeugt (keine fremden Rechte) |
| `render.js` | macht daraus die MP4-Dateien (Playwright + ffmpeg) |

Neu erzeugen (Linux/Mac mit Node, Playwright, ffmpeg, Python + numpy):
```
python3 sound.py .
node render.js "$(pwd)"
```
Texte bleiben im sicheren Bereich (nicht unter TikToks Knöpfen rechts und der Beschreibung unten).
