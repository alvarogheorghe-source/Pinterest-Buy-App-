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

## Video 4: Mali nachts auf Pinterest (Geschichte ohne Werbung, 14,5 s)

Erzähltext in *Sternchen*, ohne Marke am Ende (Werbung kommt in die Kommentare):
*scrollt um 3 uhr nachts durch pinterest* (Feed voller Hasen-Influencer) · *alle sehen so gut aus* ·
*will auch so aussehen* (Traumwolke) · *wo soll sie überhaupt suchen??* (37 Tabs) · *sucht 3 stunden* ·
*alles zu teuer* · *hat eine idee* (Sonnenaufgang). Spieluhr-Musik mit "womp womp" und "ding!".
```
python3 story_sound.py <ausgabe>
node render_story.js "$(pwd)" <ausgabe> de     # oder en
```

## Mali-Serie (serie.html): ausverkauft, paket, schrank, warenkorb

Kurze Alltagsgeschichten (10–11 s), Erzähltext in *Sternchen*, keine Werbung im Video.
Gemeinsame Bausteine (Mali, Zimmer, Bett, Text) liegen in `mali-lib.js`.
```
python3 serie_sound.py <ausgabe>
node render_serie.js "$(pwd)" <ausgabe> de     # oder en
```
Wann was gepostet wird: `docs/social/POSTING-PLAN.md`.
