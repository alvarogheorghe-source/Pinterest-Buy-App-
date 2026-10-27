"""Suchbegriffe für Shop-Schnittstellen (eBay, Etsy, ...) aus den Pins.

Jede Quelle sucht in "ihrer" Sprache: eBay.de/.at auf Deutsch ("beige oversized Pullover"),
Etsy auf Englisch ("beige oversized sweater") – dort sind die meisten Titel englisch.
"""

import math
from dataclasses import dataclass, field

from backend import details
from backend.brands import BRANDS
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, audience,
                              build_style_profile, classify_pin, find_terms, pin_text)

QUERIES_PER_DEPARTMENT = 10      # 2 Welten × 10 Suchen – gleiche Suchen teilen sich alle (search_cache.py)
BRAND_MIN_PINS = 1               # erkannte Marke/Modell -> gezielte Suche (schon ab 1 Pin)
MAX_BRAND_QUERIES = 2            # höchstens so viele der 4 Suchen pro Welt für Marken
MAX_DETAILS = 2                  # höchstens so viele Merkmale pro Suche ("Baggy Light Wash Jeans")
DETAIL_SHARE = 0.25              # Merkmal zählt, wenn es in mind. 25 % der Pins dieser Kategorie ist
MIN_RESULTS = 5                  # weniger Treffer -> zusätzlich breiter suchen (Sicherheitsnetz)
# Allgemeine Typen: bei Gleichstand gewinnt das genauere Teil ("Chelsea Boots" vor "Stiefel")
GENERIC_TYPES = {"Stiefel", "Sneaker"}
# Stile, die nur zu Kleidung passen (keine "oversized Stiefel")
CLOTHING_ONLY_STYLES = {"oversized"}


class Query(tuple):
    """Eine Suche: verhält sich wie (Suchtext, Kategorie), hat aber zusätzlich .fallback –
    eine breitere Suche für den Fall, dass die genaue zu wenig findet."""

    def __new__(cls, text: str, category: str, fallback: str | None = None):
        query = super().__new__(cls, (text, category))
        query.fallback = fallback if fallback != text else None
        return query


def search_with_fallback(search, query) -> list:
    """search(text) -> Treffer. Findet die genaue Suche zu wenig, kommt die breitere dazu
    ("Baggy Light Wash Jeans" -> "Jeans"). Doppelte Angebote sortieren die Quellen selbst aus."""
    results = search(query[0])
    fallback = getattr(query, "fallback", None)
    if len(results) < MIN_RESULTS and fallback:
        results = results + search(fallback)
    return results

# Ohne Pins: diese Kategorien zuerst
DEFAULT_CATEGORIES = {
    "mode": ["Oberteile", "Hosen", "Jacken", "Schuhe"],
    "wohnen": ["Deko", "Leuchten", "Textilien", "Möbel"],
}


@dataclass(frozen=True)
class SearchWords:
    """Wörter, die Verkäufer auf einer Plattform wirklich in ihre Titel schreiben."""
    categories: dict[str, str]                       # Kategorie -> Suchwort
    styles: dict[str, str | None]                    # Stil -> Suchwort, None = weglassen
    colors: dict[str, str] = field(default_factory=dict)  # Farbe -> Suchwort (sonst gleich)
    audience: dict[str, str] = field(default_factory=dict)  # "herren" -> "Herren"
    english: bool = False                            # Suchwörter der Details: Deutsch/Englisch
    second_hand: str = "Vintage"                     # Wort für Second-Hand-Suchen
    # Gerade gefragt (Pinterest/TikTok) – für Besucher ohne Pins und freie Plätze
    trends: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def style(self, style: str) -> str | None:
        return self.styles.get(style, style)

    def brand_query(self, name: str) -> str:
        """"Carhartt" -> "Carhartt Jacke"; Schuh-Modelle bleiben, wie sie sind."""
        brand = BRANDS[name]
        item = brand.item or ("" if brand.category == "Schuhe" else self.categories[brand.category])
        return f"{name} {item}".strip()

    def detail(self, name: str) -> str:
        found = details.BY_NAME[name]
        return found.en if self.english else found.de

    def query(self, color: str | None, style: str | None, category: str,
              adjectives: list[str] = (), noun: str | None = None) -> str:
        """Farbe + Merkmale + Stil + Teil, z.B. "schwarz Baggy Light Wash Jeans".
        noun: genaues Teil ("Hoodie") statt des allgemeinen Kategorie-Worts ("Pullover")."""
        words = [self.colors.get(color, color) if color else None,
                 *(self.detail(a) for a in adjectives),
                 self.style(style) if style else None,
                 self.detail(noun) if noun else self.categories[category]]
        words = [w for w in words if w]
        # Doppeltes weg: "Cargo Cargohose" -> "Cargohose", "Mini Mini" -> "Mini"
        kept = [w for i, w in enumerate(words)
                if not any(w.lower() in other.lower() for j, other in enumerate(words)
                           if j != i and (w.lower() != other.lower() or j < i))]
        return " ".join(kept)


GERMAN = SearchWords(
    categories={
        "Oberteile": "Pullover", "Hosen": "Hose", "Jacken": "Jacke", "Kleider & Röcke": "Kleid",
        "Schuhe": "Sneaker", "Accessoires": "Tasche",
        "Deko": "Vase", "Leuchten": "Lampe", "Textilien": "Kissen", "Küche & Tisch": "Tasse",
        "Möbel": "Beistelltisch", "Pflanzen & Töpfe": "Blumentopf", "Wandgestaltung": "Poster",
    },
    # "clean", "cozy" & Co. schreibt kaum ein Verkäufer in den Titel -> lieber breiter suchen
    styles={
        "utility": "Cargo", "goth": "Gothic", "coquette": "Schleife", "cottagecore": "Blumen",
        "natur": "Natur", "clean": None, "cozy": None, "casual": None, "sommer": "Sommer",
    },
    audience={"herren": "Herren", "damen": "Damen"},
    trends={
        "mode": [("Baggy Jeans", "Hosen"), ("Chunky Sneaker", "Schuhe"), ("Oversized Hoodie", "Oberteile"),
                 ("Vintage Lederjacke", "Jacken"), ("Cargohose", "Hosen"), ("Strickpullover", "Oberteile"),
                 ("Satin Midirock", "Kleider & Röcke"), ("Schultertasche", "Accessoires"),
                 ("Wide Leg Jeans", "Hosen"), ("Bomberjacke", "Jacken")],
        "wohnen": [("Keramikvase", "Deko"), ("Pilz Lampe", "Leuchten"), ("Boucle Kissen", "Textilien"),
                   ("Wellen Spiegel", "Wandgestaltung"), ("Rattan Lampe", "Leuchten"),
                   ("Steingut Tasse", "Küche & Tisch"), ("Duftkerze", "Deko"),
                   ("Beistelltisch Holz", "Möbel"), ("Kunstdruck Poster", "Wandgestaltung"),
                   ("Keramik Blumentopf", "Pflanzen & Töpfe")],
    },
)

ENGLISH = SearchWords(
    categories={
        "Oberteile": "sweater", "Hosen": "pants", "Jacken": "jacket", "Kleider & Röcke": "dress",
        "Schuhe": "shoes", "Accessoires": "bag",
        "Deko": "vase", "Leuchten": "lamp", "Textilien": "pillow cover", "Küche & Tisch": "mug",
        "Möbel": "side table", "Pflanzen & Töpfe": "planter", "Wandgestaltung": "poster",
    },
    styles={
        "utility": "cargo", "goth": "gothic", "coquette": "bow", "natur": "natural",
        "minimalistisch": "minimalist", "klassisch": "classic", "romantisch": "romantic",
        "sportlich": "sporty", "skandinavisch": "scandinavian", "sommer": "summer",
        "clean": None, "casual": None,
    },
    colors={
        "weiß": "white", "schwarz": "black", "grau": "grey", "braun": "brown", "blau": "blue",
        "grün": "green", "oliv": "olive", "rosa": "pink", "rot": "red", "gelb": "yellow",
        "silber": "silver",
    },
    audience={"herren": "men's", "damen": "women's"},
    english=True,
    second_hand="vintage",
    trends={
        "mode": [("baggy jeans", "Hosen"), ("chunky sneakers", "Schuhe"), ("oversized hoodie", "Oberteile"),
                 ("vintage leather jacket", "Jacken"), ("cargo pants", "Hosen"), ("knit sweater", "Oberteile"),
                 ("satin midi skirt", "Kleider & Röcke"), ("shoulder bag", "Accessoires"),
                 ("wide leg jeans", "Hosen"), ("bomber jacket", "Jacken")],
        "wohnen": [("ceramic vase", "Deko"), ("mushroom lamp", "Leuchten"), ("boucle pillow", "Textilien"),
                   ("wavy mirror", "Wandgestaltung"), ("rattan lamp", "Leuchten"),
                   ("stoneware mug", "Küche & Tisch"), ("scented candle", "Deko"),
                   ("wooden side table", "Möbel"), ("art print poster", "Wandgestaltung"),
                   ("ceramic planter", "Pflanzen & Töpfe")],
    },
)


def _top(counter) -> str | None:
    return next(iter(counter.most_common(1)), (None,))[0]


def _top_style(counter, words: SearchWords) -> str | None:
    """Häufigster Stil, den man auf der Plattform sinnvoll suchen kann."""
    return next((s for s, _ in counter.most_common() if words.style(s)), None)


def _part_words(sub, color, style, category, adjectives, words) -> tuple[str | None, str | None]:
    """Farbe und Stil für die Suche nach einem Teil – passend zu den gewählten Merkmalen."""
    part_color = _top(sub.colors) or color
    groups = {details.BY_NAME[a].group for a in adjectives}
    # Waschung sagt schon die Farbe ("Light Wash") -> keine zweite ("schwarz Light Wash")
    if "waschung" in groups:
        part_color = None
    # Stil: aus den Pins dieses Teils; der allgemeine Stil nur, wenn es keine Merkmale gibt
    part_style = _top_style(sub.styles, words) or (None if adjectives else style)
    if part_style in CLOTHING_ONLY_STYLES and (category in ("Schuhe", "Accessoires")
                                               or "schnitt" in groups):
        part_style = None                        # keine "oversized Stiefel", kein "oversized Baggy"
    if len(adjectives) >= MAX_DETAILS:           # 2 Merkmale sind genauer als jeder Stil
        part_style = None
    return part_color, part_style


def pick_details(profile, category: str) -> tuple[str | None, list[str]]:
    """Welche Merkmale kommen in die Suche? -> (genaues Teil oder None, [Merkmale])

    Nur Merkmale, die in genug Pins dieser Kategorie vorkommen; höchstens eins pro Gruppe
    (nie "Skinny Bootcut"), höchstens MAX_DETAILS. Ein einzelnes Foto zählt voll."""
    needed = max(1, math.ceil(DETAIL_SHARE * profile.categories[category]))
    noun, adjectives, groups = None, [], set()
    ranked = sorted(profile.top_details(category), key=lambda d: (-d[1], d[0] in GENERIC_TYPES))
    for name, count in ranked:
        if count < needed:
            break
        group = details.BY_NAME[name].group
        if group == "typ":
            noun = noun or name
        elif group not in groups and len(adjectives) < MAX_DETAILS:
            groups.add(group)
            adjectives.append(name)
    return noun, adjectives


def build_queries(pins: list[dict], department: str, words: SearchWords = GERMAN,
                  limit: int = QUERIES_PER_DEPARTMENT) -> list[tuple[str, str]]:
    """[(Suchtext, Kategorie), ...] – z.B. ("beige oversized Pullover", "Oberteile").

    Farbe und Stil kommen aus den Pins, in denen GENAU diese Kategorie vorkommt:
    pinnst du beige Hoodies und schwarze Cargohosen, sucht die App "beige … Pullover"
    und "schwarz Cargo Hose" – nicht alles in Beige.
    """
    profile = build_style_profile(pins, department)
    world_pins = [pin for pin in pins if department in classify_pin(pin)]
    color, style = _top(profile.colors), _top_style(profile.styles, words)
    categories = [c for c, _ in profile.categories.most_common()
                  if CATEGORY_SYNONYMS[c][0] == department]

    queries: list[tuple[str, str]] = []

    def add(query, category: str) -> None:
        query = query if isinstance(query, Query) else Query(query, category)
        if query[0] not in (text for text, _ in queries):
            queries.append(query)

    for category in categories:
        matching = [pin for pin in world_pins
                    if category in find_terms(pin_text(pin), CATEGORY_PATTERNS)
                    or category in pin.get("image_categories", [])]
        sub = build_style_profile(matching)
        noun, adjectives = pick_details(profile, category)
        part_color, part_style = _part_words(sub, color, style, category, adjectives, words)
        # Merkmale sind genauer als der Stil: bei 2 Merkmalen kein Stil-Wort mehr,
        # und "oversized" nicht neben einem Schnitt ("oversized Baggy")
        text = words.query(part_color, part_style, category, adjectives, noun)
        # Sicherheitsnetz: dasselbe Teil ohne Merkmale ("schwarz Jeans")
        add(Query(text, category, fallback=words.query(part_color, None, category, noun=noun)),
            category)

    # Ein freier Platz? Dann das Lieblingsteil auch in der zweitliebsten Farbe
    second_colors = [c for c, _ in profile.colors.most_common(2)][1:]
    if categories and second_colors:
        noun, adjectives = pick_details(profile, categories[0])
        color_fits, part_style = _part_words(profile, None, style, categories[0], adjectives, words)
        # Bei "Light Wash" & Co. keine zweite Farbe (Farbe steckt schon in der Waschung)
        second = second_colors[0] if color_fits or not adjectives else None
        add(Query(words.query(second, part_style, categories[0], adjectives, noun),
                  categories[0], fallback=words.query(second_colors[0], None, categories[0],
                                                      noun=noun)), categories[0])

    # Second Hand: das Lieblingsteil auch gezielt gebraucht/vintage ("Vintage Baggy Jeans")
    if categories and queries:
        top = queries[0]
        add(Query(f"{words.second_hand} {top[0]}", top[1],
                  fallback=f"{words.second_hand} {getattr(top, 'fallback', None) or top[0]}"), top[1])

    # Freie Plätze: mit Pins zuerst deine Farbe/dein Stil in weiteren Kategorien
    # ("beige oversized Pullover"), dann Trends – ohne Pins gleich die Trends (statt "Pullover")
    personal = [(words.query(color, None if style in CLOTHING_ONLY_STYLES
                              and c in ("Schuhe", "Accessoires") else style, c), c)
                for c in DEFAULT_CATEGORIES[department]]
    # Ein einzelnes Foto (photo.py): nur suchen, was drauf ist – keine allgemeinen Trends
    trends = [] if len(pins) == 1 else sorted(words.trends.get(department, []),
                                              key=lambda t: t[1] not in categories)
    for text, category in (personal + trends if categories or color or style else trends + personal):
        add(text, category)

    # Marke/Modell erkannt (Bild oder Text)? -> gezielte Suche ganz vorne, z.B.
    # "Onitsuka Tiger Mexico 66" oder "Carhartt Jacke". Gerade Second Hand findet man so
    # genau das Teil aus den Pins. Häufigste Marke zuerst.
    brand_queries = [(words.brand_query(brand), BRANDS[brand].category)
                     for brand, count in profile.brands.most_common(MAX_BRAND_QUERIES)
                     if count >= BRAND_MIN_PINS]
    queries = brand_queries + [q for q in queries if q not in brand_queries]
    queries = queries[:limit]

    # Mode: zeigt das Board klar Herren- oder Damenmode? -> "Herren Baggy Jeans"
    who = None
    if department == "mode":
        # Ein einzelnes Foto (photo.py): dessen Erkennung zählt direkt, sonst das ganze Board
        who = pins[0].get("image_gender") if len(pins) == 1 else audience(pins)
    if who and words.audience.get(who):
        prefix = words.audience[who]
        queries = [Query(f"{prefix} {q[0]}", q[1],
                         fallback=f"{prefix} {q.fallback}" if getattr(q, "fallback", None) else None)
                   for q in queries]
    return queries
