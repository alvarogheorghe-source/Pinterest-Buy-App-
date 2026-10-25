"""Erkennt, ob der Link eines Pins zu einem Shop oder Second-Hand-Marktplatz führt.

Viele Leute bewerben ihre Kleidung (z.B. ihren Depop-Shop) auf Pinterest. Führt
ein Pin direkt zu so einem Angebot, ist das GENAU das Teil aus dem Bild.

Wir prüfen nur die Adresse, die uns die Pinterest-API liefert – wir rufen die
Shop-Seiten selbst nicht ab (kein Scraping).
"""

import re
from urllib.parse import urlparse

SECOND_HAND = "Second Hand"
SHOP = "Shop"

# Name in der Adresse -> (Anzeigename, Art). Neue Plattform = eine Zeile mehr.
PLATFORMS = {
    "depop": ("Depop", SECOND_HAND),
    "vinted": ("Vinted", SECOND_HAND),
    "willhaben": ("willhaben", SECOND_HAND),
    "ebay": ("eBay", SECOND_HAND),
    "kleinanzeigen": ("Kleinanzeigen", SECOND_HAND),
    "etsy": ("Etsy", SECOND_HAND),
    "sellpy": ("Sellpy", SECOND_HAND),
    "zalando": ("Zalando", SHOP),
    "asos": ("ASOS", SHOP),
    "hm": ("H&M", SHOP),
    "zara": ("Zara", SHOP),
    "aboutyou": ("About You", SHOP),
}

# Erlaubte Länder-Endungen, z.B. vinted.at, zalando.de, ebay.co.uk
TLDS = r"(com|at|de|ch|co\.uk|fr|it|es|nl|pl|be|se|dk)"

# Pro Plattform ein Suchausdruck. (^|\.) erlaubt Subdomains wie "www." oder "de.",
# $ am Ende sorgt dafür, dass "depop.com.betrug.net" NICHT als Depop zählt.
PLATFORM_PATTERNS = {
    name: re.compile(rf"(^|\.){name}\.{TLDS}$") for name in PLATFORMS
}

# Typische Produkt-Adressen unbekannter Online-Shops (z.B. Shopify: /products/...)
PRODUCT_PATH = re.compile(r"/(products?|item|artikel|p)/", re.IGNORECASE)

# Diese Seiten sind keine Shops, auch wenn die Adresse danach aussieht
IGNORED_HOSTS = re.compile(r"(^|\.)(pinterest|pin|instagram|tiktok|youtube|facebook)\.")


def detect_platform(url: str | None) -> dict | None:
    """Gibt {"platform": "Depop", "platform_type": "Second Hand"} zurück – oder None."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None  # z.B. "javascript:..." – niemals verlinken

    host = parsed.hostname.lower()
    if IGNORED_HOSTS.search(host):
        return None

    for name, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(host):
            display_name, platform_type = PLATFORMS[name]
            return {"platform": display_name, "platform_type": platform_type}

    # Enthält die Adresse einen bekannten Namen, gehört aber nicht dazu
    # (z.B. "depop.com.betrug.net"), ist sie verdächtig -> lieber nicht verlinken.
    if any(name in host.split(".") for name in PLATFORMS):
        return None

    # Unbekannter Shop, aber die Adresse sieht nach einer Produktseite aus
    if PRODUCT_PATH.search(parsed.path):
        return {"platform": host.removeprefix("www."), "platform_type": SHOP}

    return None


def find_pin_items(pins: list[dict]) -> list[dict]:
    """Alle Pins, deren Link zu einem Shop/Marktplatz führt, mit Plattform-Infos."""
    items = []
    for pin in pins:
        platform = detect_platform(pin.get("link"))
        if platform:
            items.append({**pin, **platform})
    return items
