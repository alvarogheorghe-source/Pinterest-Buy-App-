"""Echte Produkte von eBay (offizielle Browse API) – neu und gebraucht.

Ablauf:
1. Aus dem Stilprofil der Pins werden Suchbegriffe gebaut, z.B. "beige oversized Pullover".
2. Die Browse API sucht damit auf eBay (nur Sofort-Kaufen).
3. Jedes Ergebnis wird ein Product: Farben, Stile und Kategorie liest die App aus dem
   Titel – danach funktioniert alles wie bisher (Ranking, ♡/👎, Bilderkennung, ...).
4. Ergebnisse werden zwischengespeichert (data/ebay_cache.json), damit nicht jeder
   Klick eine Anfrage kostet.

Zugang (kostenlos): https://developer.ebay.com -> Konto -> "Application Keys"
(Production). In .env: EBAY_CLIENT_ID und EBAY_CLIENT_SECRET.
Bitte die eBay API License Agreement lesen (z.B. Regeln zu Anzeige und Speicherdauer).

Affiliate: Mit dem eBay Partner Network (EPN) kann man an Käufen verdienen. Trägt man
die Kampagnen-ID ein (EBAY_EPN_CAMPAIGN_ID in .env), schickt die App sie an eBay mit, und
eBay liefert fertige Partnerlinks zurück (itemAffiliateWebUrl). Erst DANN sind die Links
"Werbung". Ohne EPN: "Link zu eBay".
"""

import base64
import os
import re
import time

import httpx

from backend import storage
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, build_style_profile, classify_pin, find_terms,
                              pin_text)
from backend.products import DEPARTMENTS, Product, ProductSource, ProductSourceError

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

CACHE_FILE = "ebay_cache.json"
CACHE_SECONDS = 60 * 60          # 1 Stunde zwischenspeichern
RESULTS_PER_QUERY = 20
QUERIES_PER_DEPARTMENT = 4       # 2 Welten × 4 Suchen = 8 Anfragen pro Aktualisierung

# Kategorie -> deutsches Suchwort (eBay.de/.at sucht am besten auf Deutsch)
SEARCH_WORDS = {
    "Oberteile": "Pullover", "Hosen": "Hose", "Jacken": "Jacke", "Kleider & Röcke": "Kleid",
    "Schuhe": "Sneaker", "Accessoires": "Tasche",
    "Deko": "Vase", "Leuchten": "Lampe", "Textilien": "Kissen", "Küche & Tisch": "Tasse",
    "Möbel": "Beistelltisch", "Pflanzen & Töpfe": "Blumentopf", "Wandgestaltung": "Poster",
}
# Stil -> Wort, das Verkäufer auf eBay wirklich in Titel schreiben. None = weglassen,
# weil kaum jemand so sucht ("clean", "cozy") – dann lieber breiter suchen.
STYLE_SEARCH_WORDS = {
    "utility": "Cargo", "goth": "Gothic", "coquette": "Schleife", "cottagecore": "Blumen",
    "natur": "Holz", "clean": None, "cozy": None, "casual": None, "sommer": "Sommer",
}
# Titel mit diesen Wörtern passen fast nie zu Pins: Kinder-/Puppen-/Tiersachen, Sammelpakete,
# Defektes, Ersatzteile, Schnittmuster.
JUNK_PATTERN = re.compile(
    r"\b(?:baby|kinder\w*|kids|mädchen|jungen|puppe\w*|barbie|hund(?!ezahn)\w*|katze\w*|"
    r"konvolut|paket|bundle|sammlung|lot|defekt\w*|bastler\w*|ersatzteil\w*|"
    r"schnittmuster|anleitung|aufkleber|sticker)\b", re.IGNORECASE)
MIN_PRICE = 5  # Euro – darunter fast nur Kleinkram und Lockangebote

# Ohne Pins: diese Kategorien zuerst
DEFAULT_CATEGORIES = {
    "mode": ["Oberteile", "Hosen", "Jacken", "Schuhe"],
    "wohnen": ["Deko", "Leuchten", "Textilien", "Möbel"],
}


def configured() -> bool:
    """Sind eBay-Schlüssel in .env eingetragen?"""
    return bool(os.getenv("EBAY_CLIENT_ID", "").strip() and os.getenv("EBAY_CLIENT_SECRET", "").strip())


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests eBay simulieren können."""
    return httpx.Client(timeout=15)


# --- Anmeldung (App-Token, kein Nutzer-Login nötig) ---------------------------------------

_token: dict = {}


def app_token() -> str:
    """Holt einen App-Token (gilt ca. 2 Stunden) und merkt ihn sich."""
    if _token.get("value") and _token["expires_at"] > time.time() + 60:
        return _token["value"]
    credentials = f"{os.getenv('EBAY_CLIENT_ID', '').strip()}:{os.getenv('EBAY_CLIENT_SECRET', '').strip()}"
    with _http() as client:
        response = client.post(
            TOKEN_URL,
            headers={"Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": SCOPE},
        )
    if response.status_code != 200:
        raise ProductSourceError("eBay-Anmeldung fehlgeschlagen – stimmen EBAY_CLIENT_ID und "
                                 "EBAY_CLIENT_SECRET in .env?")
    data = response.json()
    _token.update(value=data["access_token"], expires_at=time.time() + data.get("expires_in", 7200))
    return _token["value"]


# --- Suchbegriffe aus dem Stilprofil ---------------------------------------------------------

def _top(counter) -> str | None:
    return next(iter(counter.most_common(1)), (None,))[0]


def _top_style(counter) -> str | None:
    """Häufigster Stil, den man auf eBay sinnvoll suchen kann (nicht "cozy", "clean" …)."""
    return next((s for s, _ in counter.most_common() if STYLE_SEARCH_WORDS.get(s, s)), None)


def _query(color: str | None, style: str | None, category: str) -> str:
    style_word = STYLE_SEARCH_WORDS.get(style, style) if style else None
    return " ".join(w for w in (color, style_word, SEARCH_WORDS[category]) if w)


def build_queries(pins: list[dict], department: str) -> list[tuple[str, str]]:
    """[(Suchtext, Kategorie), ...] – z.B. ("beige oversized Pullover", "Oberteile").

    Farbe und Stil kommen aus den Pins, in denen GENAU diese Kategorie vorkommt:
    pinnst du beige Hoodies und schwarze Cargohosen, sucht die App "beige … Pullover"
    und "schwarz Cargo Hose" – nicht alles in Beige.
    """
    profile = build_style_profile(pins, department)
    world_pins = [pin for pin in pins if department in classify_pin(pin)]
    color, style = _top(profile.colors), _top_style(profile.styles)
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
        add(_query(_top(sub.colors) or color, _top_style(sub.styles) or style, category), category)

    # Ein freier Platz? Dann das Lieblingsteil auch in der zweitliebsten Farbe
    second_colors = [c for c, _ in profile.colors.most_common(2)][1:]
    if categories and second_colors:
        add(_query(second_colors[0], style, categories[0]), categories[0])

    for fallback in DEFAULT_CATEGORIES[department]:
        add(_query(color, style, fallback), fallback)
    return queries[:QUERIES_PER_DEPARTMENT]


def large_image(url: str) -> str:
    """eBay-Bilder gibt es in mehreren Größen (…/s-l225.jpg). Größer = bessere Bilderkennung."""
    return re.sub(r"/s-l\d+\.(jpg|jpeg|png|webp)$", r"/s-l500.\1", url)


# --- Suche und Umwandlung in Produkte ---------------------------------------------------------

def search(query: str) -> list[dict]:
    """Eine Suche auf eBay (nur Sofort-Kaufen)."""
    params = {"q": query, "limit": RESULTS_PER_QUERY,
              "filter": f"buyingOptions:{{FIXED_PRICE}},price:[{MIN_PRICE}..],priceCurrency:EUR"}
    headers = {
        "Authorization": f"Bearer {app_token()}",
        "X-EBAY-C-MARKETPLACE-ID": os.getenv("EBAY_MARKETPLACE", "").strip() or "EBAY_DE",
    }
    campaign = os.getenv("EBAY_EPN_CAMPAIGN_ID", "").strip()
    if campaign:  # eBay liefert dann Partnerlinks mit (itemAffiliateWebUrl)
        headers["X-EBAY-C-ENDUSERCTX"] = f"affiliateCampaignId={campaign}"
    with _http() as client:
        response = client.get(SEARCH_URL, params=params, headers=headers)
    if response.status_code != 200:
        raise ProductSourceError(f"eBay-Suche fehlgeschlagen ({response.status_code}).")
    return response.json().get("itemSummaries", [])


def to_product(item: dict, department: str, query_category: str) -> Product | None:
    """eBay-Ergebnis -> Product. None, wenn wichtige Angaben fehlen."""
    try:
        price = float(item["price"]["value"])
        currency = item["price"].get("currency", "EUR")
        image = (item.get("image") or {}).get("imageUrl") or \
            (item.get("thumbnailImages") or [{}])[0].get("imageUrl")
        # Partnerlink, falls eBay einen geliefert hat – sonst der normale Link
        url = item.get("itemAffiliateWebUrl") or item["itemWebUrl"]
        sponsored = "itemAffiliateWebUrl" in item
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    title = item.get("title", "")
    if not image or not url.startswith("https://") or currency != "EUR" or JUNK_PATTERN.search(title):
        return None

    # Kategorie aus dem Titel – passt sie nicht zur Welt, die der Suche
    categories = [c for c in find_terms(title, CATEGORY_PATTERNS)
                  if CATEGORY_SYNONYMS[c][0] == department]
    condition = item.get("condition", "")
    second_hand = condition and not condition.lower().startswith(("neu", "new"))
    return Product(
        id="ebay-" + re.sub(r"[^A-Za-z0-9]", "-", item["itemId"]),
        name=title[:90],
        shop="eBay · Second Hand" if second_hand else "eBay",
        price=price,
        currency=currency,
        department=department,
        category=categories[0] if categories else query_category,
        colors=sorted(find_terms(title, COLOR_PATTERNS)),
        style_tags=sorted(find_terms(title, STYLE_PATTERNS)),
        image_url=large_image(image),
        affiliate_url=url,
        sponsored=sponsored,  # nur mit Partnerlink ist es Werbung
    )


class EbayProductSource(ProductSource):
    """Produktquelle mit echten eBay-Angeboten, passend zum Stilprofil der Pins."""

    def load(self) -> list[Product]:
        cached = storage.read_json(CACHE_FILE, default=None)
        if cached and cached.get("fetched_at", 0) > time.time() - CACHE_SECONDS:
            return [Product(**p) for p in cached["products"]]

        pins = storage.load_pins()["pins"]
        products, seen = [], set()
        for department in DEPARTMENTS:
            for query, category in build_queries(pins, department):
                for item in search(query):
                    product = to_product(item, department, category)
                    if product and product.id not in seen:
                        seen.add(product.id)
                        products.append(product)

        storage.write_json(CACHE_FILE, {"fetched_at": time.time(),
                                        "products": [p.model_dump() for p in products]})
        return products


def clear_cache() -> None:
    """Nach neuen Pins: beim nächsten Laden neu suchen."""
    storage.delete_json(CACHE_FILE)
