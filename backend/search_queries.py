"""Suchbegriffe für Shop-Schnittstellen (eBay, Etsy, ...) aus den Pins.

Jede Quelle sucht in "ihrer" Sprache: eBay.de/.at auf Deutsch ("beige oversized Pullover"),
Etsy auf Englisch ("beige oversized sweater") – dort sind die meisten Titel englisch.
"""

from dataclasses import dataclass, field

from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, audience,
                              build_style_profile, classify_pin, find_terms, pin_text)

QUERIES_PER_DEPARTMENT = 4       # 2 Welten × 4 Suchen = 8 Anfragen pro Quelle und Stunde

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

    def style(self, style: str) -> str | None:
        return self.styles.get(style, style)

    def query(self, color: str | None, style: str | None, category: str) -> str:
        words = (self.colors.get(color, color) if color else None,
                 self.style(style) if style else None,
                 self.categories[category])
        return " ".join(w for w in words if w)


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
)


def _top(counter) -> str | None:
    return next(iter(counter.most_common(1)), (None,))[0]


def _top_style(counter, words: SearchWords) -> str | None:
    """Häufigster Stil, den man auf der Plattform sinnvoll suchen kann."""
    return next((s for s, _ in counter.most_common() if words.style(s)), None)


def build_queries(pins: list[dict], department: str,
                  words: SearchWords = GERMAN) -> list[tuple[str, str]]:
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

    def add(text: str, category: str) -> None:
        if text not in (q for q, _ in queries):
            queries.append((text, category))

    for category in categories:
        matching = [pin for pin in world_pins
                    if category in find_terms(pin_text(pin), CATEGORY_PATTERNS)]
        sub = build_style_profile(matching)
        add(words.query(_top(sub.colors) or color, _top_style(sub.styles, words) or style,
                        category), category)

    # Ein freier Platz? Dann das Lieblingsteil auch in der zweitliebsten Farbe
    second_colors = [c for c, _ in profile.colors.most_common(2)][1:]
    if categories and second_colors:
        add(words.query(second_colors[0], style, categories[0]), categories[0])

    for fallback in DEFAULT_CATEGORIES[department]:
        add(words.query(color, style, fallback), fallback)
    queries = queries[:QUERIES_PER_DEPARTMENT]

    # Mode: zeigt das Board klar Herren- oder Damenmode? -> "Herren Baggy Jeans"
    who = audience(pins) if department == "mode" else None
    if who and words.audience.get(who):
        queries = [(f"{words.audience[who]} {text}", category) for text, category in queries]
    return queries
