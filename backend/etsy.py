"""Echte Produkte von Etsy (offizielle Open API v3) – Vintage, Handgemachtes, Deko.

Ablauf wie bei eBay (backend/ebay.py):
1. Suchbegriffe aus den Pins – auf Englisch, weil die meisten Etsy-Titel englisch sind.
2. Suche nach aktiven Angeboten, dann ein zweiter Aufruf für Bilder und Shopnamen.
3. Jedes Ergebnis wird ein Product; danach funktioniert alles wie bisher.
4. 1 Stunde Zwischenspeicher (data/etsy_cache.json).

Zugang (kostenlos, Etsy muss die App freigeben): https://www.etsy.com/developers ->
"Your Apps". In .env: ETSY_API_KEY (Keystring) und ETSY_SHARED_SECRET (Shared Secret).

Etsy verlangt einen Hinweis, dass die App nicht von Etsy ist (ATTRIBUTION) – den zeigt
der Shop automatisch an, sobald Etsy-Produkte dabei sind.
"""

import html
import os
import re

import httpx

from backend import storage
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, find_terms)
from backend.products import DEPARTMENTS, CachedSource, Product, ProductSourceError
from backend.search_queries import ENGLISH, build_queries, search_with_fallback

API_URL = "https://openapi.etsy.com/v3/application"
RESULTS_PER_QUERY = 20
MIN_PRICE = 5  # Euro

ATTRIBUTION = ("The term 'Etsy' is a trademark of Etsy, Inc. This application uses the "
               "Etsy API but is not endorsed or certified by Etsy, Inc.")

# Auf Etsy gibt es viele digitale Dateien (Schnittmuster, Druckvorlagen) – die kann man
# nicht anziehen oder hinstellen. Dazu Kinder- und Tiersachen wie bei eBay.
JUNK_PATTERN = re.compile(
    r"\b(?:digital|download|printable|pdf|svg|png|template|pattern|tutorial|"
    r"schnittmuster|anleitung|baby|kids|toddler|kinder\w*|doll|puppe\w*|dog|cat|hund(?!ezahn)\w*|"
    r"sticker|aufkleber|bundle|lot)\b", re.IGNORECASE)


def configured() -> bool:
    """Ist ein Etsy-Schlüssel in .env eingetragen?"""
    return bool(os.getenv("ETSY_API_KEY", "").strip())


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests Etsy simulieren können."""
    return httpx.Client(timeout=15)


def _headers() -> dict:
    """Etsy erkennt die App am Header x-api-key. Steht auch das Shared Secret in .env,
    wird es mit Doppelpunkt angehängt ("keystring:secret") – so verlangt es Etsy für
    neuere Apps."""
    key = os.getenv("ETSY_API_KEY", "").strip()
    secret = os.getenv("ETSY_SHARED_SECRET", "").strip()
    return {"x-api-key": f"{key}:{secret}" if secret else key}


def _get(path: str, params: dict) -> dict:
    with _http() as client:
        response = client.get(f"{API_URL}{path}", params=params, headers=_headers())
    if response.status_code in (401, 403):
        raise ProductSourceError("Etsy-Anmeldung fehlgeschlagen – stimmen ETSY_API_KEY und "
                                 "ETSY_SHARED_SECRET in .env, und hat Etsy die App freigegeben?")
    if response.status_code != 200:
        raise ProductSourceError(f"Etsy-Suche fehlgeschlagen ({response.status_code}).")
    return response.json()


def search(query: str) -> list[dict]:
    """Sucht aktive Angebote und holt dann Bilder und Shopnamen dazu."""
    found = _get("/listings/active", {"keywords": query, "limit": RESULTS_PER_QUERY,
                                      "sort_on": "score"})
    ids = [str(listing["listing_id"]) for listing in found.get("results", [])]
    if not ids:
        return []
    details = _get("/listings/batch", {"listing_ids": ",".join(ids), "includes": "Images,Shop"})
    return details.get("results", [])


def to_product(listing: dict, department: str, query_category: str) -> Product | None:
    """Etsy-Angebot -> Product. None, wenn wichtige Angaben fehlen oder es nicht passt."""
    try:
        price = listing["price"]
        amount = price["amount"] / price["divisor"]
        currency = price["currency_code"]
        image = listing["images"][0]["url_570xN"]
        url = listing["url"]
    except (KeyError, TypeError, IndexError, ZeroDivisionError):
        return None
    title = html.unescape(listing.get("title", ""))
    if (currency != "EUR" or amount < MIN_PRICE or not url.startswith("https://")
            or listing.get("listing_type") == "download" or listing.get("is_supply")
            or JUNK_PATTERN.search(title)):
        return None

    categories = [c for c in find_terms(title, CATEGORY_PATTERNS)
                  if CATEGORY_SYNONYMS[c][0] == department]
    when_made = str(listing.get("when_made", ""))
    vintage = when_made.startswith(("19", "before_"))  # Etsy: Vintage = mind. 20 Jahre alt
    shop_name = (listing.get("shop") or {}).get("shop_name")
    # "Etsy · Vintage" oder "Etsy · <Name des Etsy-Shops>"
    shop = "Etsy · Vintage" if vintage else (f"Etsy · {shop_name}" if shop_name else "Etsy")
    return Product(
        id=f"etsy-{int(listing['listing_id'])}",
        name=title[:90],
        shop=shop,
        seller=shop_name or "",
        price=round(amount, 2),
        currency=currency,
        department=department,
        category=categories[0] if categories else query_category,
        colors=sorted(find_terms(title, COLOR_PATTERNS)),
        style_tags=sorted(find_terms(title, STYLE_PATTERNS) | ({"vintage"} if vintage else set())),
        image_url=image,
        affiliate_url=url,
        sponsored=False,  # normaler Link zu Etsy; Etsy-Partnerprogramm läuft über Awin (später)
    )


class EtsyProductSource(CachedSource):
    """Produktquelle mit echten Etsy-Angeboten, passend zum Stilprofil der Pins."""

    name = "etsy"
    cache_file = "etsy_cache.json"

    def fetch(self) -> list[Product]:
        return self.fetch_for(storage.load_pins()["pins"], DEPARTMENTS)

    def fetch_for(self, pins: list[dict], departments, keep=None) -> list[Product]:
        """Suche passend zu beliebigen Pins (auch zu einem hochgeladenen Foto).
        keep(query, category) -> False überspringt eine Suche."""
        products, seen = [], set()
        for department in departments:
            for planned in build_queries(pins, department, ENGLISH):
                query, category = planned
                if keep and not keep(query, category):
                    continue
                for listing in search_with_fallback(search, planned):
                    product = to_product(listing, department, category)
                    if product and product.id not in seen:
                        seen.add(product.id)
                        products.append(product)
        return products
