"""Produkte von AliExpress (offizielles Partnerprogramm, "AliExpress Portals" / Open Platform).

Ablauf wie bei eBay/Etsy:
1. Suchbegriffe aus den Pins (Englisch) – aber NIE nach Marken (counterfeit.py)
2. Suche über die Affiliate-API (aliexpress.affiliate.product.query), Preise in Euro,
   Versand ins Land der Person (region.py)
3. Fälschungs-Filter: Angebote mit Markennamen oder Fake-Wörtern fliegen raus
   -> "Der Look – ohne Fake."
4. 1 Stunde Zwischenspeicher (pro Person)

Zugang: Partnerprogramm von AliExpress (portals.aliexpress.com) + App auf der Open Platform
(openservice.aliexpress.com). In .env: ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET,
ALIEXPRESS_TRACKING_ID. Die Links sind Partnerlinks -> immer als "Werbung" gekennzeichnet.

Hinweis: Gegen die echte API konnte das noch nicht getestet werden (Zugang fehlt) – die
Antwort wird deshalb vorsichtig gelesen; fehlende Felder führen zum Überspringen.
"""

import hashlib
import hmac
import os
import re
import time

import httpx

from backend import region, shops, storage
from backend.i18n import tr
from backend.counterfeit import looks_like_fake, mentions_brand
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, find_terms)
from backend.products import DEPARTMENTS, CachedSource, Product, ProductSourceError
from backend.search_queries import ENGLISH, build_queries, search_with_fallback

API_URL = "https://api-sg.aliexpress.com/sync"
METHOD = "aliexpress.affiliate.product.query"
RESULTS_PER_QUERY = 20
MIN_PRICE = 5  # Euro


def configured() -> bool:
    return all(os.getenv(name, "").strip() for name in
               ("ALIEXPRESS_APP_KEY", "ALIEXPRESS_APP_SECRET", "ALIEXPRESS_TRACKING_ID"))


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests AliExpress simulieren können."""
    return httpx.Client(timeout=15)


def sign(params: dict, secret: str) -> str:
    """Signatur der Open Platform: Parameter nach Namen sortiert, Name+Wert aneinander,
    HMAC-SHA256 mit dem App-Secret, als Großbuchstaben-Hex."""
    text = "".join(f"{key}{params[key]}" for key in sorted(params))
    return hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest().upper()


def search(query: str) -> list[dict]:
    params = {
        "app_key": os.getenv("ALIEXPRESS_APP_KEY", "").strip(),
        "method": METHOD,
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "keywords": query,
        "page_size": str(RESULTS_PER_QUERY),
        "target_currency": region.current().currency,
        "target_language": "DE",
        "ship_to_country": region.current().code,      # ins Land der Person (region.py)
        "tracking_id": os.getenv("ALIEXPRESS_TRACKING_ID", "").strip(),
    }
    params["sign"] = sign(params, os.getenv("ALIEXPRESS_APP_SECRET", "").strip())
    with _http() as client:
        response = client.post(API_URL, data=params)
    if response.status_code != 200:
        raise ProductSourceError(tr("AliExpress-Suche fehlgeschlagen ({code}).", code=response.status_code))
    data = response.json()
    if "error_response" in data:
        raise ProductSourceError("AliExpress-Anmeldung fehlgeschlagen – stimmen ALIEXPRESS_APP_KEY, "
                                 "ALIEXPRESS_APP_SECRET und ALIEXPRESS_TRACKING_ID in .env?")
    try:
        result = data["aliexpress_affiliate_product_query_response"]["resp_result"]
        if str(result.get("resp_code")) != "200":
            return []                                    # z.B. keine Treffer
        return result["result"]["products"]["product"]
    except (KeyError, TypeError):
        return []


def to_product(item: dict, department: str, query_category: str) -> Product | None:
    """AliExpress-Angebot -> Product. None, wenn Angaben fehlen – oder es nach Fake aussieht."""
    title = str(item.get("product_title") or "")
    store = str(item.get("shop_id") or "")
    # Fälschungs-Filter – außer bei geprüften offiziellen Markenstores (backend/shops.py)
    if not title or (looks_like_fake(title) and not shops.is_trusted("aliexpress", store)):
        return None
    try:
        price = float(item.get("target_sale_price") or item.get("sale_price"))
        currency = item.get("target_sale_price_currency") or region.current().currency
        url = item.get("promotion_link") or ""
        image = item.get("product_main_image_url") or ""
        product_id = re.sub(r"[^0-9A-Za-z]", "", str(item["product_id"]))
    except (KeyError, TypeError, ValueError):
        return None
    if currency != region.current().currency or price < MIN_PRICE or not url.startswith("https://") \
            or not image.startswith("https://") or not product_id:
        return None

    categories = [c for c in find_terms(title, CATEGORY_PATTERNS)
                  if CATEGORY_SYNONYMS[c][0] == department]
    return Product(
        id=f"aliexpress-{product_id}",
        name=title[:90],
        shop="AliExpress",
        seller=store,
        price=round(price, 2),
        currency=currency,
        department=department,
        category=categories[0] if categories else query_category,
        colors=sorted(find_terms(title, COLOR_PATTERNS)),
        style_tags=sorted(find_terms(title, STYLE_PATTERNS)),
        image_url=image,
        affiliate_url=url,
        sponsored=True,   # Partnerlink (tracking_id) -> immer "Werbung"
    )


def no_brand_searches(query: str, category: str) -> bool:
    """Bei AliExpress nie nach Marken suchen – dort wären es fast nur Fälschungen."""
    return not mentions_brand(query)


class AliExpressProductSource(CachedSource):
    """Markenlose Teile im Stil der Pins – "Der Look – ohne Fake"."""

    name = "aliexpress"
    cache_file = "aliexpress_cache.json"

    def fetch(self) -> list[Product]:
        return self.fetch_for(storage.load_pins()["pins"], DEPARTMENTS)

    def fetch_for(self, pins: list[dict], departments, keep=None) -> list[Product]:
        products, seen = [], set()
        for department in departments:
            for planned in build_queries(pins, department, ENGLISH):
                query, category = planned
                if not no_brand_searches(query, category) or (keep and not keep(query, category)):
                    continue
                for item in search_with_fallback(search, planned):
                    product = to_product(item, department, category)
                    if product and product.id not in seen:
                        seen.add(product.id)
                        products.append(product)
        return products
