"""Was die Vibe-Karte über eine Person sagt: drei Eigenschaften, eine Superkraft, ein
Signature-Piece und der Vibe, der perfekt dazu passt (zum Markieren von Freund:innen).

Alles bewusst schmeichelhaft und ehrlich gemeint: Man soll sich gut fühlen und die Karte gern
in die Story stellen. Keine erfundenen Zahlen.
Neuer Vibe in vibe.py -> hier einen Eintrag ergänzen (Test: tests/test_vibe.py).
"""

# Vibe -> (Deutsch, Englisch)
PROFILES = {
    "Goth Baddie": (
        {"traits": ["mutig", "geheimnisvoll", "loyal"], "piece": "Schwarze Lederjacke",
         "power": "Du betrittst einen Raum und alle wollen wissen, wer du bist.", "duo": "Clean Girl"},
        {"traits": ["bold", "mysterious", "loyal"], "piece": "Black leather jacket",
         "power": "You walk into a room and everyone wants to know who you are.", "duo": "Clean Girl"}),
    "Clean Girl": (
        {"traits": ["ruhig", "organisiert", "strahlend"], "piece": "Goldene Creolen",
         "power": "Du machst aus einem ganz normalen Dienstag einen Glow-Moment.", "duo": "Quiet Luxury"},
        {"traits": ["calm", "put together", "glowing"], "piece": "Gold hoops",
         "power": "You turn an ordinary Tuesday into a glow moment.", "duo": "Quiet Luxury"}),
    "Streetwear Icon": (
        {"traits": ["selbstbewusst", "kreativ", "immer vorne dabei"], "piece": "Chunky Sneaker",
         "power": "Was du heute trägst, tragen die anderen nächsten Monat.", "duo": "Y2K Baby"},
        {"traits": ["confident", "creative", "ahead of the curve"], "piece": "Chunky sneakers",
         "power": "What you wear today, everyone else wears next month.", "duo": "Y2K Baby"}),
    "Cozy Era": (
        {"traits": ["warmherzig", "gemütlich", "ein sicherer Hafen"], "piece": "Oversized Strickpulli",
         "power": "Bei dir fühlen sich alle sofort zuhause.", "duo": "Cottagecore"},
        {"traits": ["warm-hearted", "cozy", "a safe place"], "piece": "Oversized knit sweater",
         "power": "Everyone feels at home around you.", "duo": "Cottagecore"}),
    "Quiet Luxury": (
        {"traits": ["elegant", "souverän", "detailverliebt"], "piece": "Cashmere-Pullover",
         "power": "Du musst nie laut sein, um aufzufallen.", "duo": "Clean Girl"},
        {"traits": ["elegant", "composed", "detail-obsessed"], "piece": "Cashmere sweater",
         "power": "You never have to be loud to stand out.", "duo": "Clean Girl"}),
    "Thrift Legend": (
        {"traits": ["einzigartig", "nachhaltig", "abenteuerlustig"], "piece": "Vintage-Lederjacke",
         "power": "Du findest Schätze, wo andere nur Kleiderständer sehen.", "duo": "Festival Boho"},
        {"traits": ["one of a kind", "sustainable", "adventurous"], "piece": "Vintage leather jacket",
         "power": "You find treasures where others just see clothing racks.", "duo": "Festival Boho"}),
    "Y2K Baby": (
        {"traits": ["verspielt", "furchtlos", "nostalgisch"], "piece": "Baby Tee",
         "power": "Du bringst jedes Gruppenfoto zum Glitzern.", "duo": "Coquette Era"},
        {"traits": ["playful", "fearless", "nostalgic"], "piece": "Baby tee",
         "power": "You make every group photo sparkle.", "duo": "Coquette Era"}),
    "Festival Boho": (
        {"traits": ["frei", "herzlich", "sonnig"], "piece": "Fransentasche",
         "power": "Mit dir fühlt sich jeder Tag wie Sommer an.", "duo": "Thrift Legend"},
        {"traits": ["free-spirited", "warm", "sunny"], "piece": "Fringe bag",
         "power": "Every day feels like summer with you.", "duo": "Thrift Legend"}),
    "Coquette Era": (
        {"traits": ["romantisch", "zart", "liebevoll"], "piece": "Satinschleife",
         "power": "Du machst aus kleinen Dingen etwas ganz Besonderes.", "duo": "Y2K Baby"},
        {"traits": ["romantic", "soft", "caring"], "piece": "Satin bow",
         "power": "You turn little things into something special.", "duo": "Y2K Baby"}),
    "Cottagecore": (
        {"traits": ["sanft", "kreativ", "naturverbunden"], "piece": "Blumenkleid",
         "power": "Du hast die Gabe, das Schöne im Kleinen zu sehen.", "duo": "Cozy Era"},
        {"traits": ["gentle", "creative", "nature-loving"], "piece": "Floral dress",
         "power": "You have a gift for finding beauty in small things.", "duo": "Cozy Era"}),
    "Japandi Zen": (
        {"traits": ["ruhig", "klar", "achtsam"], "piece": "Leinenhemd",
         "power": "In deiner Nähe wird alles ein bisschen leiser und schöner.", "duo": "Quiet Luxury"},
        {"traits": ["calm", "clear-minded", "mindful"], "piece": "Linen shirt",
         "power": "Everything gets a little calmer and prettier around you.", "duo": "Quiet Luxury"}),
    "Athleisure Era": (
        {"traits": ["energiegeladen", "motiviert", "unaufhaltsam"], "piece": "Lieblings-Leggings",
         "power": "Du schaffst an einem Vormittag, wofür andere eine Woche brauchen.", "duo": "Streetwear Icon"},
        {"traits": ["energetic", "driven", "unstoppable"], "piece": "Favourite leggings",
         "power": "You get done in a morning what takes others a week.", "duo": "Streetwear Icon"}),
    "Gorpcore": (
        {"traits": ["abenteuerlustig", "praktisch", "furchtlos"], "piece": "Fleecejacke",
         "power": "Du bist bereit für jedes Wetter und jedes Abenteuer.", "duo": "Effortless Cool"},
        {"traits": ["adventurous", "practical", "fearless"], "piece": "Fleece jacket",
         "power": "You're ready for any weather and any adventure.", "duo": "Effortless Cool"}),
    "Effortless Cool": (
        {"traits": ["entspannt", "lässig", "echt"], "piece": "Weiße Sneaker",
         "power": "Du siehst immer gut aus, und es wirkt nie nach Mühe.", "duo": "Clean Fit"},
        {"traits": ["laid-back", "easygoing", "real"], "piece": "White sneakers",
         "power": "You always look good, and it never looks like effort.", "duo": "Clean Fit"}),
    "Clean Fit": (
        {"traits": ["klar", "stilsicher", "verlässlich"], "piece": "Perfekt sitzendes Hemd",
         "power": "Du weißt genau, was dir steht, und das sieht man.", "duo": "Effortless Cool"},
        {"traits": ["sharp", "self-assured", "reliable"], "piece": "Perfectly fitted shirt",
         "power": "You know exactly what suits you, and it shows.", "duo": "Effortless Cool"}),
    "Main Character": (
        {"traits": ["einzigartig", "mutig", "unberechenbar"], "piece": "Was du gerade trägst",
         "power": "Du folgst keinem Trend. Trends folgen dir.", "duo": None},
        {"traits": ["one of a kind", "bold", "unpredictable"], "piece": "Whatever you're wearing",
         "power": "You don't follow trends. Trends follow you.", "duo": None}),
}


def profile(title: str, lang: str) -> dict | None:
    entry = PROFILES.get(title)
    return entry[1 if lang == "en" else 0] if entry else None
