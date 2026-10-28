"""Amazon-Partnerprogramm (PartnerNet) – ohne Produkt-Schnittstelle.

Amazons Produkt-API gibt es erst nach den ersten 3 Verkäufen. Bis dahin verdienen wir so:
- Amazon-Links (z.B. in Pins) bekommen die Partner-ID angehängt
- "Bei Amazon suchen"-Links mit Begriffen, die Mali erkannt hat (Foto-Suche, Produktseite)
Alles, was jemand danach innerhalb von 24 Stunden bei Amazon kauft, zählt als Verkauf.

.env:  AMAZON_PARTNER_TAG=malipin-21   (kein Geheimnis, steht in jedem Link)
Die Partner-ID mit "-21" gilt für amazon.de. Das liefert nach Österreich, Deutschland und in
die Schweiz – nur dort zeigen wir die Links.
"""

import os
import re
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from backend import region

DOMAIN = "www.amazon.de"
COUNTRIES = {"AT", "DE", "CH"}
AMAZON_DE = re.compile(r"^(?:www\.|smile\.)?amazon\.de$", re.I)


def partner_tag() -> str:
    return os.getenv("AMAZON_PARTNER_TAG", "").strip()


def available() -> bool:
    """Partner-ID eingetragen und die Person ist in einem Land, das amazon.de beliefert?"""
    return bool(partner_tag()) and region.current().code in COUNTRIES


def terms_for(product: dict) -> list[str]:
    """Suchbegriffe zu einem Produkt: Farbe, Stil, Kategorie, für wen (z.B. schwarz baggy Jeans damen)."""
    return [*product.get("colors", [])[:1], *product.get("style_tags", [])[:1],
            product.get("category", ""), product.get("gender") or ""]


def search_url(terms: list[str]) -> str | None:
    """Suchergebnis-Seite bei Amazon mit unserer Partner-ID (None, wenn nicht verfügbar)."""
    words = " ".join(dict.fromkeys(t.strip() for t in terms if t and t.strip()))
    if not words or not available():
        return None
    return f"https://{DOMAIN}/s?k={quote_plus(words)}&tag={quote_plus(partner_tag())}"


def apply(item: dict) -> dict:
    """amazon.de-Links eines Produkts/Pin-Teils bekommen die Partner-ID (-> "Werbung")."""
    if not partner_tag():
        return item
    for key in ("affiliate_url", "link"):
        url = item.get(key)
        if isinstance(url, str) and url.startswith("http"):
            tagged = tag(url)
            if tagged != url:
                item[key] = tagged
                item["sponsored"] = True
    return item


def tag(url: str) -> str:
    """Partner-ID anhängen. Hat der Link schon eine (z.B. von der Person, die den Pin
    erstellt hat), bleibt er unverändert – deren Provision nehmen wir niemandem weg."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not AMAZON_DE.match(parts.hostname or "") or any(k == "tag" for k, _ in query):
        return url
    query.append(("tag", partner_tag()))
    return urlunsplit(parts._replace(query=urlencode(query)))
