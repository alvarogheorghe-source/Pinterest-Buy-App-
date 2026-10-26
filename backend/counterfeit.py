"""Fälschungs-Filter: "Der Look – ohne Fake."

Auf großen Marktplätzen aus Fernost (AliExpress …) tragen Angebote mit Markennamen im Titel
sehr oft Fälschungen ("Reps"). Wer dorthin verlinkt und daran verdient, riskiert Ärger mit
Markenrechten und mit den Partnerprogrammen. Darum: Bei solchen Quellen zeigt Malipin NUR
markenlose Teile im gleichen Stil – Angebote mit Markennamen oder typischen Fake-Wörtern
fliegen raus.

Nicht für eBay (dort gibt es viel echte Second-Hand-Markenware) – nur für Quellen, die das
ausdrücklich nutzen (aliexpress.py).
"""

import re

from backend.brands import BRANDS

# Bekannte Marken, die besonders oft gefälscht werden (zusätzlich zu brands.py)
EXTRA_BRANDS = [
    "nike", "adidas", "jordan", "yeezy", "new balance", "converse", "vans", "puma", "reebok",
    "gucci", "prada", "louis vuitton", "chanel", "dior", "balenciaga", "versace", "fendi",
    "hermes", "hermès", "burberry", "saint laurent", "ysl", "miu miu", "loewe", "celine",
    "bottega", "givenchy", "valentino", "moncler", "canada goose", "stone island", "off-white",
    "off white", "fear of god", "essentials", "chrome hearts", "bape", "supreme", "palm angels",
    "goyard", "rolex", "cartier", "tiffany", "ray-ban", "rayban", "oakley", "lacoste",
    "tommy hilfiger", "calvin klein", "levi's", "levis", "carhartt", "stussy", "stüssy",
    "the north face", "north face", "arcteryx", "arc'teryx", "patagonia", "ralph lauren",
    "ugg", "birkenstock", "dr martens", "dr. martens", "onitsuka", "asics", "salomon",
    "lululemon", "alo yoga", "skims", "zara", "h&m",
]
# Typische Wörter in Fake-Angeboten
FAKE_WORDS = ["replica", "replika", "1:1", "aaa quality", "aaa+", "mirror quality", "fake",
              "counterfeit", "inspired by", "high quality copy", "reps"]


def _pattern() -> re.Pattern:
    words = set(EXTRA_BRANDS) | {w for brand in BRANDS.values() for w in brand.words}
    words |= {name.lower() for name in BRANDS}
    words |= set(FAKE_WORDS)
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![\w]){'(?:' + alternatives + ')'}(?![\w])", re.IGNORECASE)


_FAKE = _pattern()


def looks_like_fake(title: str) -> bool:
    """True, wenn der Titel eine Marke oder ein typisches Fake-Wort enthält."""
    return bool(_FAKE.search(title or ""))


def mentions_brand(text: str) -> bool:
    """Für Suchbegriffe: bei diesen Quellen nie nach Marken suchen."""
    return looks_like_fake(text)
