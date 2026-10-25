"""Schritt 5: Einfaches Matching ohne KI.

Zwei getrennte Teile:
1. build_style_profile(pins)  -> zählt Farb- und Stilwörter in Titel + Beschreibung
2. rank_products(products, profile) -> sortiert Produkte nach Überschneidung mit dem Profil

In Phase 2 kann build_style_profile() durch eine Bilderkennungs-API ersetzt werden.
Solange sie ein StyleProfile mit denselben Begriffen zurückgibt, bleibt rank_products() gleich.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from backend.products import Product

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
    "orange": ["orange", "terracotta", "rust", "rost"],
    "gelb": ["gelb", "yellow", "mustard", "senf"],
    "silber": ["silber", "silver"],
}

STYLE_SYNONYMS = {
    "streetwear": ["streetwear", "street style", "streetstyle", "skater", "hypebeast"],
    "oversized": ["oversized", "oversize", "baggy", "loose fit"],
    "minimalistisch": ["minimalistisch", "minimalist", "minimal", "minimalism"],
    "clean": ["clean", "clean look", "clean girl"],
    "vintage": ["vintage", "retro", "90s", "70s", "thrift", "thrifted", "secondhand"],
    "y2k": ["y2k", "2000s", "00s"],
    "casual": ["casual", "lässig", "everyday", "alltag"],
    "elegant": ["elegant", "chic", "classy", "schick"],
    "klassisch": ["klassisch", "classic", "timeless", "old money"],
    "boho": ["boho", "bohemian", "hippie"],
    "sportlich": ["sportlich", "sporty", "athleisure", "gym"],
    "cozy": ["cozy", "cosy", "gemütlich", "comfy"],
    "sommer": ["sommer", "summer"],
    "winter": ["winter"],
    "romantisch": ["romantisch", "romantic", "feminine", "floral", "geblümt"],
    "utility": ["utility", "cargo"],
    "outdoor": ["outdoor", "gorpcore", "hiking"],
}


def _compile(synonyms: dict[str, list[str]]) -> dict[str, re.Pattern]:
    """Baut pro Begriff einen Suchausdruck. \\b = Wortgrenze, damit z.B. "red"
    nicht in "redesign" gefunden wird."""
    return {
        term: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b")
        for term, words in synonyms.items()
    }


COLOR_PATTERNS = _compile(COLOR_SYNONYMS)
STYLE_PATTERNS = _compile(STYLE_SYNONYMS)


@dataclass
class StyleProfile:
    """Das Stilprofil: in wie vielen Pins kommt welcher Begriff vor?"""
    pin_count: int = 0
    colors: Counter = field(default_factory=Counter)
    styles: Counter = field(default_factory=Counter)

    def weight(self, term: str) -> float:
        """Anteil der Pins mit diesem Begriff (0.0 bis 1.0)."""
        if self.pin_count == 0:
            return 0.0
        return (self.colors[term] + self.styles[term]) / self.pin_count

    def mentions(self, term: str) -> int:
        return self.colors[term] + self.styles[term]

    def to_dict(self) -> dict:
        return {
            "pin_count": self.pin_count,
            "colors": dict(self.colors.most_common()),
            "styles": dict(self.styles.most_common()),
            "top_colors": [term for term, _ in self.colors.most_common(3)],
            "top_styles": [term for term, _ in self.styles.most_common(3)],
        }


def find_terms(text: str, patterns: dict[str, re.Pattern]) -> set[str]:
    """Welche festen Begriffe kommen in einem Text vor? (als Menge -> jeder nur einmal)"""
    text = text.lower()
    return {term for term, pattern in patterns.items() if pattern.search(text)}


def build_style_profile(pins: list[dict]) -> StyleProfile:
    """Zählt für jeden Begriff, in wie vielen Pins er vorkommt.

    PHASE 2: Diese Funktion kann durch eine Bilderkennung ersetzt werden, die
    aus pin["image_url"] Farben und Stile erkennt und dasselbe StyleProfile liefert.
    """
    profile = StyleProfile(pin_count=len(pins))
    for pin in pins:
        text = f"{pin.get('title', '')} {pin.get('description', '')}"
        profile.colors.update(find_terms(text, COLOR_PATTERNS))
        profile.styles.update(find_terms(text, STYLE_PATTERNS))
    return profile


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


def rank_products(products: list[Product], profile: StyleProfile) -> list[dict]:
    """Sortiert Produkte: beste Übereinstimmung zuerst, bei Gleichstand günstigere zuerst."""
    results = []
    for product in products:
        terms = product.colors + product.style_tags
        # Nur Begriffe, die im Profil vorkommen; häufigste zuerst
        matched = sorted((t for t in terms if profile.mentions(t) > 0),
                         key=profile.weight, reverse=True)
        score = sum(profile.weight(t) for t in matched)
        results.append({
            **product.model_dump(),
            "score": round(score, 3),
            "matched": matched,
            "reason": explain(matched, profile),
        })

    # Minus vor dem Score -> absteigend; Preis -> aufsteigend
    results.sort(key=lambda r: (-r["score"], r["price"]))
    return results
