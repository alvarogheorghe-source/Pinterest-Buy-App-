"""Einfaches Matching ohne KI – für Kleidung (Mode) und Gegenstände (Wohnen).

Teile:
1. classify_pin(pin)                   -> zeigt der Pin Mode, Wohnen oder beides?
2. build_style_profile(pins, department) -> zählt Farben, Stile und Kategorien
3. rank_products(products, profile)   -> sortiert Produkte nach Überschneidung

In Phase 2 kann build_style_profile() durch eine Bilderkennung ersetzt werden.
Solange sie ein StyleProfile mit denselben Begriffen zurückgibt, bleibt rank_products() gleich.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from backend.brands import BRANDS
from backend.products import DEPARTMENTS, Product

# Feste Begriffe (wie in products.json) -> Wörter, die in Pins dafür stehen können.
# Pins sind oft Englisch, deshalb Deutsch UND Englisch.
COLOR_SYNONYMS = {
    "beige": ["beige", "sand", "creme", "cream", "camel", "nude", "ecru", "taupe"],
    "weiß": ["weiß", "weiss", "white", "offwhite", "off-white"],
    "schwarz": ["schwarz", "black"],
    "grau": ["grau", "grey", "gray", "anthrazit", "charcoal"],
    "braun": ["braun", "brown", "cognac", "chocolate", "schoko"],
    "blau": ["blau", "blue", "navy", "hellblau"],
    "grün": ["grün", "gruen", "green", "salbei", "sage", "mint"],
    "oliv": ["oliv", "olive", "khaki"],
    "rosa": ["rosa", "pink", "rose", "altrosa"],
    "rot": ["rot", "red", "bordeaux", "burgundy", "weinrot"],
    "orange": ["orange", "terracotta", "terrakotta", "rust", "rost"],
    "gelb": ["gelb", "yellow", "mustard", "senf"],
    "silber": ["silber", "silver"],
    "gold": ["gold", "golden", "messing", "brass"],
}

STYLE_SYNONYMS = {
    # Mode
    "streetwear": ["streetwear", "street style", "streetstyle", "skater", "hypebeast"],
    "oversized": ["oversized", "oversize", "baggy", "loose fit"],
    "y2k": ["y2k", "2000s", "00s"],
    "casual": ["casual", "lässig", "everyday", "alltag"],
    "sportlich": ["sportlich", "sporty", "athleisure", "gym"],
    "romantisch": ["romantisch", "romantic", "feminine", "floral", "geblümt"],
    "utility": ["utility", "cargo"],
    "outdoor": ["outdoor", "gorpcore", "hiking"],
    "sommer": ["sommer", "summer"],
    "winter": ["winter"],
    # Mode UND Wohnen
    "minimalistisch": ["minimalistisch", "minimalist", "minimal", "minimalism"],
    "clean": ["clean", "clean look", "clean girl"],
    "vintage": ["vintage", "retro", "90s", "70s", "thrift", "thrifted", "secondhand"],
    "elegant": ["elegant", "chic", "classy", "schick"],
    "klassisch": ["klassisch", "classic", "timeless", "old money"],
    "boho": ["boho", "bohemian", "hippie"],
    "cozy": ["cozy", "cosy", "gemütlich", "comfy", "hygge"],
    # Wohnen
    "skandinavisch": ["skandinavisch", "scandi", "scandinavian", "nordic", "nordisch"],
    "japandi": ["japandi", "wabi sabi", "wabi-sabi"],
    "industrial": ["industrial", "industrie", "loft"],
    "modern": ["modern", "contemporary"],
    "natur": ["natur", "natural", "rattan", "jute", "holz", "wood", "wooden", "leinen", "linen"],
    # Ästhetiken, vor allem für den Vibe von Mali (vibe.py)
    "goth": ["goth", "gothic", "witchy", "dark aesthetic", "dark academia"],
    "grunge": ["grunge"],
    "coquette": ["coquette", "bow", "bows", "schleife", "schleifen", "balletcore"],
    "cottagecore": ["cottagecore", "cottage core"],
}

# Kategorie -> (Welt, Wörter). Englische Mehrzahl mit -s/-es wird automatisch erkannt.
# "*" = darf am Ende eines deutschen zusammengesetzten Wortes stehen ("*vase" -> "Glasvase").
# Nur bei Wörtern, die dabei nichts Falsches finden: "*tisch" würde "praktisch",
# "*decke" "Entdecke", "*rock" "Barock" und "*teller" "Hersteller" finden!
CATEGORY_SYNONYMS = {
    # Bewusst ohne "tee": auf Deutsch ist das ein Getränk
    "Oberteile": ("mode", ["hoodie", "*pullover", "sweater", "*shirt", "t-shirt", "top",
                           "*bluse", "blouse", "*hemd", "knit", "crop top", "cardigan",
                           "tanktop", "tank top", "polo", "korsett", "corset", "longsleeve",
                           "turtleneck", "*rollkragen", "sweatshirt", "crewneck", "bodysuit",
                           "trikot", "jersey"]),
    "Hosen": ("mode", ["*hose", "pants", "*jeans", "trousers", "sweatpants", "shorts", "jorts",
                       "leggings", "jogger", "joggers", "cargos", "slacks"]),
    "Jacken": ("mode", ["*jacke", "jacket", "*coat", "*mantel", "trench", "puffer", "blazer",
                        "bomber", "parka", "windbreaker", "sakko", "weste", "gilet"]),
    "Kleider & Röcke": ("mode", ["*kleid", "dress", "rock", "minirock", "jeansrock",
                                 "faltenrock", "plisseerock", "skirt", "jumpsuit"]),
    "Schuhe": ("mode", ["*schuhe", "shoe", "*sneaker", "boot", "*stiefel", "ballerinas",
                        "loafer", "sandalen", "sandals", "heels", "pumps", "clogs",
                        "mary janes", "stiefelette", "stiefeletten", "trainers"]),
    "Accessoires": ("mode", ["*tasche", "bag", "tote", "schmuck", "jewelry", "jewellery",
                             "kette", "necklace", "*gürtel", "belt", "beanie", "*mütze", "cap",
                             "rucksack", "backpack", "ohrringe", "earrings", "creolen",
                             "armband", "bracelet", "sonnenbrille", "sunglasses", "schal",
                             "scarf", "clutch", "claw clip"]),
    "Deko": ("wohnen", ["*vase", "*vasen", "*kerze", "*kerzen", "candle", "deko", "decor",
                        "dekoration"]),
    "Leuchten": ("wohnen", ["*lampe", "*lampen", "lamp", "*leuchte", "*lichterkette",
                            "fairy light", "pendant light"]),
    "Textilien": ("wohnen", ["*kissen", "pillow", "cushion", "decke", "strickdecke", "kuscheldecke", "wolldecke",
                             "tagesdecke", "bettdecke", "blanket", "throw",
                             "*teppich", "rug", "*bettwäsche", "bedding", "*vorhang", "curtain"]),
    "Küche & Tisch": ("wohnen", ["*tasse", "*tassen", "mug", "*geschirr", "teller", "plate",
                                 "*brett", "tableware", "küche", "kitchen"]),
    "Möbel": ("wohnen", ["sofa", "couch", "*stuhl", "chair", "tisch", "tische", "table",
                         "*regal", "shelf", "shelves", "möbel", "furniture", "beistelltisch",
                         "esstisch", "couchtisch", "*kommode"]),
    "Pflanzen & Töpfe": ("wohnen", ["*pflanze", "*pflanzen", "plant", "*topf", "pot",
                                    "planter"]),
    "Wandgestaltung": ("wohnen", ["poster", "wall art", "*wandbild", "bilderrahmen", "frame",
                                  "*spiegel", "mirror", "gallery wall"]),
}

# Allgemeine Wörter, die eine Welt verraten, ohne eine Kategorie zu nennen
# (Auch typische Board-Namen wie "Outfits", "Mode", "Wohnideen")
DEPARTMENT_WORDS = {
    "mode": ["outfit", "outfits", "ootd", "fashion", "mode", "kleidung", "clothing",
             "streetwear", "fit check"],
    "wohnen": ["interior", "einrichtung", "home decor", "wohnzimmer", "living room",
               "schlafzimmer", "bedroom", "wohnung", "apartment", "zuhause", "interior design",
               "badezimmer", "bathroom", "wohnen", "wohnideen", "küche"],
}


def _word_pattern(word: str) -> str:
    """Ein Wort als Suchausdruck. Ein * vorne erlaubt deutsche zusammengesetzte
    Wörter: "*vase" findet auch "Keramikvase" und "Glasvase"."""
    if word.startswith("*"):
        return r"\w*" + re.escape(word[1:])
    return re.escape(word)


def _compile(synonyms: dict[str, list[str]], suffix: str = "") -> dict[str, re.Pattern]:
    """Baut pro Begriff einen Suchausdruck. \\b = Wortgrenze, damit z.B. "red"
    nicht in "redesign" gefunden wird. suffix erlaubt Endungen (Plural, Adjektiv)."""
    return {
        term: re.compile(r"\b(?:" + "|".join(_word_pattern(w) for w in words) + r")"
                         + suffix + r"\b")
        for term, words in synonyms.items()
    }


PLURAL = "(?:s|es)?"
# Deutsche Adjektiv-Endungen: "schwarze Jacke", "beiger Pullover", "weißes Regal"
ADJECTIVE = "e?[rsnm]?"  # schwarz-e, schwarz-er, beige-r, weiß-es ...

COLOR_PATTERNS = _compile(COLOR_SYNONYMS, suffix=ADJECTIVE)
STYLE_PATTERNS = _compile(STYLE_SYNONYMS)
CATEGORY_PATTERNS = _compile({c: words for c, (_, words) in CATEGORY_SYNONYMS.items()},
                             suffix=PLURAL)
DEPARTMENT_PATTERNS = _compile(DEPARTMENT_WORDS)
BRAND_PATTERNS = _compile({name: list(brand.words) for name, brand in BRANDS.items()})


@dataclass
class StyleProfile:
    """Das Stilprofil: in wie vielen Pins kommt welcher Begriff vor?"""
    pin_count: int = 0
    colors: Counter = field(default_factory=Counter)
    styles: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)  # z.B. "Deko": 3
    brands: Counter = field(default_factory=Counter)      # z.B. "Adidas Samba": 2
    # Schnitt & Details pro Kategorie (details.py), z.B. ("Hosen", "Bootcut"): 4
    details: Counter = field(default_factory=Counter)

    def mentions(self, term: str) -> int:
        """In wie vielen Pins kommt der Begriff (Farbe, Stil, Kategorie oder Detail) vor?"""
        return (self.colors[term] + self.styles[term] + self.categories[term]
                + sum(n for (_, name), n in self.details.items() if name == term))

    def detail_share(self, category: str, name: str) -> float:
        """Anteil der Pins einer Kategorie mit diesem Detail: 4 von 8 Hosen-Pins Bootcut -> 0.5"""
        pins = self.categories[category]
        return min(1.0, self.details[(category, name)] / pins) if pins else 0.0

    def top_details(self, category: str) -> list[tuple[str, int]]:
        """[("Baggy", 9), ("Light Wash", 6), …] – häufigste zuerst."""
        return [(name, n) for (c, name), n in self.details.most_common() if c == category]

    def weight(self, term: str) -> float:
        """Anteil der Pins mit diesem Begriff (0.0 bis 1.0)."""
        if self.pin_count == 0:
            return 0.0
        return self.mentions(term) / self.pin_count

    def to_dict(self) -> dict:
        return {
            "pin_count": self.pin_count,
            "colors": dict(self.colors.most_common()),
            "styles": dict(self.styles.most_common()),
            "categories": dict(self.categories.most_common()),
            "top_colors": [term for term, _ in self.colors.most_common(3)],
            "top_styles": [term for term, _ in self.styles.most_common(3)],
            "top_categories": [term for term, _ in self.categories.most_common(3)],
            "brands": dict(self.brands.most_common()),
            "details": {category: dict(self.top_details(category))
                        for category in self.categories if self.top_details(category)},
        }


def find_terms(text: str, patterns: dict[str, re.Pattern]) -> set[str]:
    """Welche festen Begriffe kommen in einem Text vor? (als Menge -> jeder nur einmal)"""
    text = text.lower()
    return {term for term, pattern in patterns.items() if pattern.search(text)}


def pin_text(pin: dict) -> str:
    """Alle Texte eines Pins: Titel, Beschreibung, Alt-Text und Name des Boards."""
    parts = ["title", "description", "alt_text", "board_name"]
    return " ".join(pin.get(part) or "" for part in parts)


# Bildfarbe -> Farbname. Pinterest liefert pro Bild eine Hauptfarbe ("#d3bf9f").
# Wir suchen die nächstliegende unserer Farben (Abstand im RGB-Farbraum).
# Weiß, Grau, Silber, Gold fehlen hier bewusst – siehe color_from_hex().
COLOR_REFERENCES = {
    "beige": (216, 195, 165),
    "braun": (123, 90, 60),
    "oliv": (107, 112, 72),
    "grün": (122, 158, 126),
    "blau": (90, 130, 180),
    "rosa": (232, 180, 188),
    "rot": (180, 40, 50),
    "orange": (200, 105, 63),
    "gelb": (225, 190, 60),
    "schwarz": (30, 30, 30),
}


def color_from_hex(hex_color: str | None) -> str | None:
    """"#d3bf9f" -> "beige". None, wenn die Farbe wohl nur der Hintergrund ist.

    Die Hauptfarbe eines Pins ist oft die weiße Wand oder das graue Studio
    dahinter. Fast weiße und farblose (graue) Töne ignorieren wir deshalb –
    Weiß und Grau erkennt die App dann nur aus dem Text.
    """
    if not hex_color or not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_color):
        return None
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    brightest, darkest = max(r, g, b), min(r, g, b)
    if darkest > 225:                                   # fast weiß
        return None
    if brightest - darkest < 18 and brightest > 60:     # grau (aber nicht schwarz)
        return None

    def distance(reference: tuple[int, int, int]) -> int:
        return sum((a - b) ** 2 for a, b in zip((r, g, b), reference))

    return min(COLOR_REFERENCES, key=lambda name: distance(COLOR_REFERENCES[name]))


def classify_pin(pin: dict) -> set[str]:
    """Zeigt der Pin Kleidung ("mode"), Gegenstände ("wohnen") oder beides?

    Ohne klares Wort gehört der Pin zu BEIDEN Welten – z.B. "beige neutral tones":
    Lieblingsfarben gelten meist für Kleidung und Wohnung.
    """
    text = pin_text(pin)
    departments = find_terms(text, DEPARTMENT_PATTERNS)
    for category in find_terms(text, CATEGORY_PATTERNS) | set(pin.get("image_categories", [])):
        departments.add(CATEGORY_SYNONYMS[category][0])
    return departments or set(DEPARTMENTS)


def build_style_profile(pins: list[dict], department: str | None = None) -> StyleProfile:
    """Zählt für jeden Begriff, in wie vielen Pins er vorkommt.

    department="mode"/"wohnen": nur Pins dieser Welt zählen. None: alle Pins.

    PHASE 2: Diese Funktion kann durch eine Bilderkennung ersetzt werden, die
    aus pin["image_url"] Farben, Stile und Gegenstände erkennt und dasselbe
    StyleProfile liefert.
    """
    if department:
        pins = [pin for pin in pins if department in classify_pin(pin)]
    profile = StyleProfile(pin_count=len(pins))
    for pin in pins:
        text = pin_text(pin)
        colors = find_terms(text, COLOR_PATTERNS)
        # Bildfarbe nur, wenn das Bild Mode/Wohnen zeigt (nicht z.B. ein Essensfoto)
        image_color = color_from_hex(pin.get("dominant_color")) \
            if pin.get("image_relevant") is not False else None
        if image_color:
            colors.add(image_color)  # Menge -> zählt pro Pin trotzdem nur einmal
        profile.colors.update(colors)
        # Begriffe aus dem Text + was die Bilderkennung im Bild gesehen hat (image_tags.py)
        profile.styles.update(find_terms(text, STYLE_PATTERNS) | set(pin.get("image_styles", [])))
        categories = find_terms(text, CATEGORY_PATTERNS) | set(pin.get("image_categories", []))
        if department:  # nur Kategorien der gewählten Welt
            categories = {c for c in categories if CATEGORY_SYNONYMS[c][0] == department}
        profile.categories.update(categories)
        # Schnitt & Details (details.py): aus dem Text + was die Bilderkennung gesehen hat
        found = details.find(text, categories) | {
            (c, name) for c, name in pin.get("image_details", []) if c in categories}
        profile.details.update(found)
        # Marken (brands.py): aus dem Text oder aus dem Bild
        brands = find_terms(text, BRAND_PATTERNS) | set(pin.get("image_brands", []))
        profile.brands.update(b for b in brands
                              if not department or CATEGORY_SYNONYMS[BRANDS[b].category][0] == department)
    return profile


# Herren- oder Damenmode? Wörter im Pin-Text (Deutsch + Englisch)
AUDIENCE_PATTERNS = _compile({
    "herren": ["herren", "männer", "men's", "mens", "menswear", "boyfriend", "guys"],  # nicht "man" (deutsch!)
    "damen": ["damen", "frauen", "women's", "womens", "womenswear", "woman", "girl", "girls",
              "ladies"],
})
AUDIENCE_SHARE = 0.7   # so viele der eindeutigen Mode-Pins müssen in eine Richtung zeigen
AUDIENCE_MIN_PINS = 3


def audience(pins: list[dict]) -> str | None:
    """"herren", "damen" oder None (gemischt / unklar / zu wenig Pins).

    Zählt pro Mode-Pin: das Wort im Text, sonst was die Bilderkennung gesehen hat.
    """
    votes = Counter()
    for pin in pins:
        if "mode" not in classify_pin(pin):
            continue
        words = find_terms(pin_text(pin), AUDIENCE_PATTERNS)
        if len(words) == 1:
            votes[words.pop()] += 1
        elif pin.get("image_gender"):
            votes[pin["image_gender"]] += 1
    total = sum(votes.values())
    if total < AUDIENCE_MIN_PINS:
        return None
    winner, count = votes.most_common(1)[0]
    return winner if count / total >= AUDIENCE_SHARE else None


def explain(matched: list[str], profile: StyleProfile) -> str:
    """Ein Satz, warum ein Produkt passt."""
    if not matched:
        return "Kein direkter Treffer mit deinem Stilprofil – zum Entdecken."

    def pins_text(term: str) -> str:
        n = profile.mentions(term)
        return f"{term} ({n} {'Pin' if n == 1 else 'Pins'})"

    top = matched[:2]  # die zwei wichtigsten Gründe reichen
    if len(top) == 1:
        return f"Passt zu dir, weil {pins_text(top[0])} oft in deinen Pins vorkommt."
    return (f"Passt zu dir, weil {pins_text(top[0])} und {pins_text(top[1])} "
            f"oft in deinen Pins vorkommen.")


DETAIL_WEIGHT = 0.6     # Bootcut gepinnt + Bootcut im Titel -> bis zu 0.6 Punkte extra
DETAIL_CLASH = 0.4      # Bootcut gepinnt, Titel sagt "Skinny" -> bis zu 0.4 Punkte weniger


def detail_points(product: Product, profile: StyleProfile) -> tuple[float, list[str]]:
    """Punkte für Schnitt & Details im Produkttitel -> (Punkte, passende Details).

    Plus, wenn ein gepinntes Detail im Titel steht. Minus, wenn der Titel in derselben
    Gruppe etwas anderes sagt, das du NICHT pinnst (Skinny statt Bootcut)."""
    found = {name for _, name in details.find(product.name, [product.category])}
    points, matched = 0.0, []
    for name in found:
        share = profile.detail_share(product.category, name)
        if share > 0:
            points += DETAIL_WEIGHT * share
            matched.append(name)
            continue
        group = details.BY_NAME[name].group
        rivals = [profile.detail_share(product.category, other)
                  for other, _ in profile.top_details(product.category)
                  if details.BY_NAME[other].group == group]
        if group != "typ" and rivals:     # Typ-Unterschiede regelt schon die Kategorie
            points -= DETAIL_CLASH * max(rivals)
    return points, sorted(matched, key=lambda n: -profile.detail_share(product.category, n))


def rank_products(products: list[Product], profile: StyleProfile) -> list[dict]:
    """Sortiert Produkte: beste Übereinstimmung zuerst, bei Gleichstand günstigere zuerst.

    Punkte gibt es für passende Farben, Stile, die Kategorie UND Schnitt & Details:
    Zeigen viele Pins Vasen, kommen Vasen weiter nach oben; pinnst du Bootcut-Jeans,
    kommen Bootcut-Jeans vor Skinny-Jeans.
    """
    results = []
    for product in products:
        terms = [product.category] + product.colors + product.style_tags
        # Nur Begriffe, die im Profil vorkommen; häufigste zuerst
        matched = sorted((t for t in terms if profile.mentions(t) > 0),
                         key=profile.weight, reverse=True)
        extra, matched_details = detail_points(product, profile)
        score = sum(profile.weight(t) for t in matched) + extra
        matched = matched_details + matched   # das genaueste Merkmal zuerst in der Begründung
        results.append({
            **product.model_dump(),
            "score": round(score, 3),
            "matched": matched,
            "reason": explain(matched, profile),
        })

    # Minus vor dem Score -> absteigend; Preis -> aufsteigend
    results.sort(key=lambda r: (-r["score"], r["price"]))
    return results


# Ganz unten, weil details.py selbst Bausteine von hier benutzt (_compile, find_terms)
from backend import details  # noqa: E402
