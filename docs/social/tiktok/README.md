# TikTok-Teaser (Malipin)

Drei 12-Sekunden-Videos im Mali-Pixel-Look, 1080×1920, jedes mit eigener Musik (150 BPM): 1 Chiptune, 2 Lo-Fi, 3 Trap.

| Datei | Inhalt |
|---|---|
| `video.html` | Animation, Bild für Bild (`?v=1`, `?v=2`, `?v=3`) |
| `sound.py` | Musik + Effekte, selbst erzeugt (keine fremden Rechte) |
| `render.js` | macht daraus die MP4-Dateien (Playwright + ffmpeg) |

Neu erzeugen (Linux/Mac mit Node, Playwright, ffmpeg, Python + numpy):
```
python3 sound.py .
node render.js "$(pwd)"        # Deutsch
node render.js "$(pwd)" en     # Englisch
```
Texte bleiben im sicheren Bereich (nicht unter TikToks Knöpfen rechts und der Beschreibung unten).

## Video 4: "ich jeden abend auf pinterest" (Mali-Geschichte, 15 s)

Weniger Werbung, mehr Mali: Mali scrollt, fragt sich, woher alle ihre Outfits haben, sucht
stundenlang (zu teuer, ausverkauft), hat eine Idee und baut Malipin. Spieluhr-Musik mit
traurigem "womp womp" und fröhlichem Ende.
```
python3 story_sound.py <ausgabe>
node render_story.js "$(pwd)" <ausgabe> de     # oder en
```
