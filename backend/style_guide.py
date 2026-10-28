"""Stil-Lexikon: Was bedeutet "Goth Baddie", "Clean Girl", "Japandi" …? (Seite /stile.html)

Zwei Teile:
- VIBES:  die Vibes aus Malis Vibe-Check (vibe.py) – ausführlich erklärt, mit typischen Teilen
- STYLES: die einzelnen Stil-Begriffe, die Malipin in Pins erkennt (matching.STYLE_SYNONYMS)

Jeder Eintrag hat eine Adresse (slug) für Links: /stile.html#vibe-goth-baddie,
/stile.html#stil-goth. So kann jede Stelle der App einen Begriff verlinken.

Neue Vibes/Stile: hier einen Eintrag ergänzen (Deutsch + Englisch). Der Test
tests/test_style_guide.py prüft, dass kein Vibe und kein Stil ohne Erklärung bleibt.
"""

from backend import i18n
from backend.vibe import LOOKS, SWATCHES, UNIQUE, VIBES, slug


# Vibe -> (Deutsch, Englisch): about = was steckt dahinter, pieces = typische Teile
VIBE_TEXTS = {
    "Goth Baddie": (
        {"about": "Dunkel, selbstbewusst und ein bisschen mysteriös. Schwarz von Kopf bis Fuß, "
                  "dazu Silber, Leder und eine Prise Grunge – aber immer mit Glamour statt Grusel.",
         "pieces": ["Schwarze Lederjacke", "Plateau-Boots", "Silberschmuck", "Mesh- oder Spitzentop"]},
        {"about": "Dark, confident and a little mysterious. Black from head to toe, with silver, "
                  "leather and a hint of grunge – glamorous rather than spooky.",
         "pieces": ["Black leather jacket", "Platform boots", "Silver jewellery", "Mesh or lace top"]}),
    "Clean Girl": (
        {"about": "Gepflegt, ruhig und mühelos. Helle Basics, glatte Haare, goldene Creolen – "
                  "der Look wirkt, als hätte er fünf Minuten gedauert (hat er nicht).",
         "pieces": ["Weißes Tanktop", "Leinenhose", "Goldene Creolen", "Ballerinas"]},
        {"about": "Polished, calm and effortless. Light basics, sleek hair, gold hoops – a look "
                  "that seems to take five minutes (it doesn't).",
         "pieces": ["White tank top", "Linen trousers", "Gold hoops", "Ballet flats"]}),
    "Streetwear Icon": (
        {"about": "Oversized, sportlich und laut. Sneaker sind das Herzstück, Hoodies und Cargo "
                  "das Fundament – inspiriert von Skate-, Hip-Hop- und Sneaker-Kultur.",
         "pieces": ["Oversized Hoodie", "Cargohose", "Chunky Sneaker", "Cap"]},
        {"about": "Oversized, sporty and loud. Sneakers are the centrepiece, hoodies and cargos "
                  "the foundation – inspired by skate, hip-hop and sneaker culture.",
         "pieces": ["Oversized hoodie", "Cargo pants", "Chunky sneakers", "Cap"]}),
    "Cozy Era": (
        {"about": "Weich, warm und gemütlich. Grobstrick, Erdtöne und alles, worin man sich "
                  "einkuscheln will – zu Hause genauso wie draußen.",
         "pieces": ["Grobstrickpullover", "Strickdecke", "Wollsocken", "Kerzen"]},
        {"about": "Soft, warm and snug. Chunky knits, earthy tones and everything you'd want to "
                  "curl up in – at home or out and about.",
         "pieces": ["Chunky knit jumper", "Knitted throw", "Wool socks", "Candles"]}),
    "Quiet Luxury": (
        {"about": "Edel ohne Logo. Hochwertige Stoffe, gedeckte Farben, klare Schnitte – man "
                  "erkennt die Qualität, nicht die Marke. Auch als „Old Money“ bekannt.",
         "pieces": ["Kaschmirpullover", "Bundfaltenhose", "Loafer", "Trenchcoat"]},
        {"about": "Refined without logos. Quality fabrics, muted colours, clean cuts – you notice "
                  "the quality, not the brand. Also known as “old money”.",
         "pieces": ["Cashmere jumper", "Pleated trousers", "Loafers", "Trench coat"]}),
    "Thrift Legend": (
        {"about": "Second Hand mit Geschichte. Einzelstücke aus den 70ern bis 90ern, gemischt zu "
                  "einem Look, den sonst niemand hat – nachhaltig und einzigartig.",
         "pieces": ["Vintage-Lederjacke", "Levi's 501", "Retro-Sweatshirt", "Secondhand-Fund"]},
        {"about": "Second-hand with a story. One-offs from the 70s to the 90s, mixed into a look "
                  "nobody else has – sustainable and unique.",
         "pieces": ["Vintage leather jacket", "Levi's 501", "Retro sweatshirt", "Thrift find"]}),
    "Y2K Baby": (
        {"about": "Die 2000er sind zurück: Low-Rise, Baby Tees, Glitzer, Pastell und ein bisschen "
                  "Popstar-Energie. Verspielt, laut und mit Absicht ein bisschen drüber.",
         "pieces": ["Baby Tee", "Low-Rise-Jeans", "Mini-Schultertasche", "Butterfly-Clips"]},
        {"about": "The 2000s are back: low-rise, baby tees, glitter, pastels and a bit of pop-star "
                  "energy. Playful, loud and a little extra on purpose.",
         "pieces": ["Baby tee", "Low-rise jeans", "Mini shoulder bag", "Butterfly clips"]}),
    "Festival Boho": (
        {"about": "Frei, warm und naturverbunden. Fransen, Häkel, Leinen und Erdtöne – irgendwo "
                  "zwischen Festival-Sonnenuntergang und Strandhaus.",
         "pieces": ["Häkeltop", "Maxikleid", "Fransenjacke", "Rattan-Tasche"]},
        {"about": "Free-spirited, warm and close to nature. Fringe, crochet, linen and earthy "
                  "tones – somewhere between a festival sunset and a beach house.",
         "pieces": ["Crochet top", "Maxi dress", "Fringe jacket", "Rattan bag"]}),
    "Coquette Era": (
        {"about": "Verspielt-romantisch: Schleifen, Spitze, Rosa und Ballerinas. Inspiriert von "
                  "Ballett und alten Liebesfilmen – zart, süß und sehr feminin.",
         "pieces": ["Schleifen-Haarband", "Spitzentop", "Ballerinas", "Faltenrock"]},
        {"about": "Playfully romantic: bows, lace, pink and ballet flats. Inspired by ballet and "
                  "old love films – delicate, sweet and very feminine.",
         "pieces": ["Bow hair ribbon", "Lace top", "Ballet flats", "Pleated skirt"]}),
    "Cottagecore": (
        {"about": "Das romantische Landleben: Blumenkleider, Leinen, Körbe und Wildblumen. "
                  "Langsam, gemütlich und ein bisschen wie aus einem Ghibli-Film.",
         "pieces": ["Blumenkleid", "Puffärmel-Bluse", "Weidenkorb", "Strickjacke"]},
        {"about": "Romantic country life: floral dresses, linen, baskets and wildflowers. Slow, "
                  "cosy and a bit like a Ghibli film.",
         "pieces": ["Floral dress", "Puff-sleeve blouse", "Wicker basket", "Cardigan"]}),
    "Japandi Zen": (
        {"about": "Japanische Ruhe trifft skandinavische Gemütlichkeit. Helles Holz, Leinen, "
                  "wenige Dinge und viel Raum – Wohnen zum Durchatmen.",
         "pieces": ["Holz-Beistelltisch", "Leinen-Bettwäsche", "Keramikvase", "Papierleuchte"]},
        {"about": "Japanese calm meets Scandinavian cosiness. Light wood, linen, few things and "
                  "lots of space – a home that lets you breathe.",
         "pieces": ["Wooden side table", "Linen bedding", "Ceramic vase", "Paper lamp"]}),
    "Athleisure Era": (
        {"about": "Sportkleidung, die man auch zum Kaffee anzieht. Leggings, Sweats und Sneaker – "
                  "bequem, aktiv und trotzdem durchgestylt.",
         "pieces": ["Leggings", "Crewneck-Sweater", "Laufschuhe", "Sport-BH-Top"]},
        {"about": "Sportswear you'd also wear to brunch. Leggings, sweats and sneakers – "
                  "comfortable, active and still put together.",
         "pieces": ["Leggings", "Crewneck sweatshirt", "Running shoes", "Sports top"]}),
    "Gorpcore": (
        {"about": "Outdoor-Funktion als Mode: Fleece, Softshell, Trail-Sneaker und Cargo. "
                  "Sieht nach Berg aus, wird aber genauso gern in der Stadt getragen.",
         "pieces": ["Fleecejacke", "Windbreaker", "Trail-Sneaker", "Cargohose"]},
        {"about": "Outdoor gear as fashion: fleece, softshell, trail sneakers and cargos. "
                  "Looks mountain-ready, but is worn just as happily in the city.",
         "pieces": ["Fleece jacket", "Windbreaker", "Trail sneakers", "Cargo pants"]}),
    "Effortless Cool": (
        {"about": "Lässig, entspannt und nie zu bemüht. Weite Jeans, ein gutes T-Shirt, saubere "
                  "Sneaker – Basics, die zusammen einfach stimmen.",
         "pieces": ["Baggy Jeans", "Weißes T-Shirt", "Saubere Sneaker", "Overshirt"]},
        {"about": "Relaxed, laid-back and never trying too hard. Wide jeans, a good tee, clean "
                  "sneakers – basics that simply work together.",
         "pieces": ["Baggy jeans", "White t-shirt", "Clean sneakers", "Overshirt"]}),
    "Clean Fit": (
        {"about": "Minimal und präzise: Schwarz, Weiß, Grau, gute Passform, keine Logos. Wenige "
                  "Teile, die perfekt sitzen und alles miteinander kombinierbar sind.",
         "pieces": ["Schlichter Pullover", "Gerade Hose", "Weiße Ledersneaker", "Mantel"]},
        {"about": "Minimal and precise: black, white, grey, good fit, no logos. A few pieces "
                  "that fit perfectly and all go together.",
         "pieces": ["Plain jumper", "Straight trousers", "White leather sneakers", "Coat"]}),
    "Main Character": (
        {"about": "Kein Vibe passt eindeutig – und das ist ein Kompliment. Du mischst Stile auf "
                  "deine eigene Art. Malis Tipp: Schau dir an, welche Begriffe er in deinen Pins findet.",
         "pieces": ["Dein Lieblingsteil", "Ein mutiger Mix", "Etwas Vintage", "Etwas Neues"]},
        {"about": "No single vibe fits – and that's a compliment. You mix styles your own way. "
                  "Mali's tip: look at which terms he finds in your pins.",
         "pieces": ["Your favourite piece", "A bold mix", "Something vintage", "Something new"]}),
}

# Stil-Begriff -> (Name DE, Name EN, Erklärung DE, Erklärung EN)
STYLE_TEXTS = {
    "streetwear": ("Streetwear", "Streetwear",
                   "Mode von der Straße: Hoodies, Sneaker, Caps, oft oversized und mit Logos.",
                   "Fashion from the street: hoodies, sneakers, caps, often oversized and logo-heavy."),
    "oversized": ("Oversized", "Oversized",
                  "Bewusst weit geschnitten – Baggy Jeans, große Hoodies, lockere Mäntel.",
                  "Deliberately loose – baggy jeans, big hoodies, relaxed coats."),
    "y2k": ("Y2K", "Y2K", "Der Look der frühen 2000er: Low-Rise, Baby Tees, Glitzer, Pastell.",
            "The early-2000s look: low-rise, baby tees, glitter, pastels."),
    "casual": ("Casual", "Casual", "Alltagstauglich und entspannt – Jeans, T-Shirt, Sneaker.",
               "Everyday and relaxed – jeans, tee, sneakers."),
    "sportlich": ("Sportlich", "Sporty", "Sport-Teile im Alltag: Leggings, Sweats, Laufschuhe.",
                  "Sportswear in everyday life: leggings, sweats, running shoes."),
    "romantisch": ("Romantisch", "Romantic", "Weich und feminin: Blumen, Rüschen, Spitze, Pastell.",
                   "Soft and feminine: florals, ruffles, lace, pastels."),
    "utility": ("Utility", "Utility", "Praktisch wie Arbeitskleidung: Cargotaschen, Overshirts, Westen.",
                "Practical like workwear: cargo pockets, overshirts, vests."),
    "outdoor": ("Outdoor", "Outdoor", "Funktion für draußen: Fleece, Softshell, Trail-Sneaker.",
                "Built for outdoors: fleece, softshell, trail sneakers."),
    "sommer": ("Sommer", "Summer", "Leicht und luftig: Leinen, Shorts, Sandalen, helle Farben.",
               "Light and airy: linen, shorts, sandals, bright colours."),
    "winter": ("Winter", "Winter", "Warm geschichtet: Strick, Wolle, Mäntel, Boots.",
               "Warm layers: knits, wool, coats, boots."),
    "minimalistisch": ("Minimalistisch", "Minimalist",
                       "Weniger ist mehr: schlichte Formen, ruhige Farben, keine Muster.",
                       "Less is more: simple shapes, calm colours, no patterns."),
    "clean": ("Clean", "Clean", "Aufgeräumt und gepflegt – helle Basics, klare Linien.",
              "Neat and polished – light basics, clean lines."),
    "vintage": ("Vintage", "Vintage", "Alte Teile mit Charakter, oft Second Hand, 70er bis 90er.",
                "Old pieces with character, often second-hand, 70s to 90s."),
    "elegant": ("Elegant", "Elegant", "Schick und erwachsen: fließende Stoffe, Blazer, feine Details.",
                "Chic and grown-up: fluid fabrics, blazers, fine details."),
    "klassisch": ("Klassisch", "Classic", "Zeitlose Teile, die nie aus der Mode kommen – Trench, Loafer, Kaschmir.",
                  "Timeless pieces that never go out of style – trench, loafers, cashmere."),
    "boho": ("Boho", "Boho", "Frei und naturverbunden: Fransen, Häkel, Maxikleider, Rattan.",
             "Free-spirited and natural: fringe, crochet, maxi dresses, rattan."),
    "cozy": ("Cozy", "Cozy", "Kuschelig und warm: Grobstrick, Decken, Kerzenlicht.",
             "Snug and warm: chunky knits, throws, candlelight."),
    "skandinavisch": ("Skandinavisch", "Scandinavian",
                      "Hell, schlicht, gemütlich: helles Holz, Weiß, Textilien.",
                      "Light, simple, cosy: pale wood, white, textiles."),
    "japandi": ("Japandi", "Japandi", "Japanisch + skandinavisch: ruhige Formen, Holz, Leinen, Keramik.",
                "Japanese + Scandinavian: calm shapes, wood, linen, ceramics."),
    "industrial": ("Industrial", "Industrial", "Loft-Look: Metall, Beton, dunkles Holz, offene Glühbirnen.",
                   "Loft look: metal, concrete, dark wood, exposed bulbs."),
    "modern": ("Modern", "Modern", "Zeitgemäß und klar: glatte Flächen, klare Formen, wenig Deko.",
               "Contemporary and clean: smooth surfaces, clear shapes, little decor."),
    "natur": ("Natur", "Natural", "Natürliche Materialien: Holz, Rattan, Jute, Leinen.",
              "Natural materials: wood, rattan, jute, linen."),
    "goth": ("Goth", "Goth", "Dunkel und dramatisch: Schwarz, Silber, Spitze, Plateau.",
             "Dark and dramatic: black, silver, lace, platforms."),
    "grunge": ("Grunge", "Grunge", "Bewusst ungeschliffen: Flanell, zerrissene Jeans, Boots – 90er-Rock.",
               "Deliberately rough: flannel, ripped jeans, boots – 90s rock."),
    "coquette": ("Coquette", "Coquette", "Schleifen, Spitze, Rosa – verspielt-feminin wie im Ballett.",
                 "Bows, lace, pink – playfully feminine, ballet-inspired."),
    "cottagecore": ("Cottagecore", "Cottagecore", "Landleben-Romantik: Blumenkleider, Körbe, Leinen.",
                    "Country-life romance: floral dresses, baskets, linen."),
}


def vibe_slug(title: str) -> str:
    return "vibe-" + slug(title)


def style_slug(term: str) -> str:
    return "stil-" + slug(term)


def guide(lang: str | None = None) -> dict:
    """Alles für die Seite /stile.html – in der Sprache der Person."""
    en = (lang or i18n.current()) == "en"
    vibes = []
    for vibe in [*VIBES, UNIQUE]:
        texts = VIBE_TEXTS[vibe.title][1 if en else 0]
        vibes.append({
            "slug": vibe_slug(vibe.title),
            "title": i18n.tr(vibe.title, "en" if en else "de"),
            "emoji": vibe.emoji,
            "look": LOOKS.get(vibe.title, "rosa"),
            "about": texts["about"],
            "pieces": texts["pieces"],
            "mali": i18n.tr(vibe.lines[0], "en" if en else "de") if vibe.lines else "",
            "colors": [SWATCHES[t] for t in vibe.terms if t in SWATCHES],
            "styles": [{"slug": style_slug(t), "name": STYLE_TEXTS[t][1 if en else 0]}
                       for t in vibe.terms if t in STYLE_TEXTS],
        })
    styles = []
    for term, (de_name, en_name, de_about, en_about) in STYLE_TEXTS.items():
        styles.append({
            "slug": style_slug(term),
            "name": en_name if en else de_name,
            "about": en_about if en else de_about,
            "vibes": [{"slug": vibe_slug(v.title), "title": i18n.tr(v.title, "en" if en else "de")}
                      for v in VIBES if term in v.terms],
        })
    styles.sort(key=lambda s: s["name"].lower())
    return {"vibes": vibes, "styles": styles}
