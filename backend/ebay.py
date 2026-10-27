"""Echte Produkte von eBay (offizielle Browse API) – neu und gebraucht.

Ablauf:
1. Aus dem Stilprofil der Pins werden Suchbegriffe gebaut, z.B. "beige oversized Pullover".
2. Die Browse API sucht damit auf eBay (nur Sofort-Kaufen).
3. Jedes Ergebnis wird ein Product: Farben, Stile und Kategorie liest die App aus dem
   Titel – danach funktioniert alles wie bisher (Ranking, ♡/👎, Bilderkennung, ...).
4. Ergebnisse werden zwischengespeichert (data/ebay_cache.json, siehe
   products.CachedSource), damit nicht jeder Klick eine Anfrage kostet.

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

from backend import quality, region, search_cache, storage
from backend.i18n import tr
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, find_terms, gender_of)
from backend.products import DEPARTMENTS, CachedSource, Product, ProductSourceError, sale_price
from backend.search_queries import ENGLISH, GERMAN, build_queries, run_parallel, search_with_fallback

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SANDBOX_HOST = "https://api.sandbox.ebay.com"   # Sandbox-Keys (…-SBX-…): eBays Testdaten
SCOPE = "https://api.ebay.com/oauth/api_scope"

RESULTS_PER_QUERY = 100     # eBay erlaubt bis 200 – eBay ist unsere Hauptquelle
QUERIES = 16                # Suchen pro Welt (Etsy/AliExpress: 10) – geteilt über search_cache
# Nur diese Felder werden zwischengespeichert (search_cache.py) – der Rest wird nicht gebraucht
KEEP_FIELDS = ("itemId", "title", "price", "condition", "image", "thumbnailImages", "itemWebUrl",
               "itemAffiliateWebUrl", "seller", "marketingPrice")

# Titel mit diesen Wörtern passen fast nie zu Pins: Kinder-/Puppen-/Tiersachen, Sammelpakete,
# Defektes, Ersatzteile, Schnittmuster.
JUNK_PATTERN = re.compile(
    r"\b(?:baby|kinder\w*|kids|mädchen|jungen|puppe\w*|barbie|hund(?!ezahn)\w*|katze\w*|"
    r"konvolut|paket|bundle|sammlung|lot|defekt\w*|bastler\w*|ersatzteil\w*|"
    r"schnittmuster|anleitung|aufkleber|sticker)\b", re.IGNORECASE)
MIN_PRICE = 5  # Euro – darunter fast nur Kleinkram und Lockangebote


def configured() -> bool:
    """Sind eBay-Schlüssel in .env eingetragen?"""
    return bool(os.getenv("EBAY_CLIENT_ID", "").strip() and os.getenv("EBAY_CLIENT_SECRET", "").strip())


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests eBay simulieren können."""
    return httpx.Client(timeout=15)


# --- Anmeldung (App-Token, kein Nutzer-Login nötig) ---------------------------------------

_token: dict = {}


def search_words():
    """Deutsche Suchwörter für ebay.at/.de/.ch, englische für ebay.com/.co.uk/…"""
    return GERMAN if region.current().search_lang == "de" else ENGLISH


def sandbox() -> bool:
    """Sandbox-Keys erkennt man am "-SBX-" in der App ID. Dort gibt es nur wenige Testangebote –
    gut, um die Anmeldung zu prüfen; für echte Angebote braucht es die Production-Keys."""
    return "-SBX-" in os.getenv("EBAY_CLIENT_ID", "")


def _url(url: str) -> str:
    return url.replace("https://api.ebay.com", SANDBOX_HOST) if sandbox() else url


def app_token() -> str:
    """Holt einen App-Token (gilt ca. 2 Stunden) und merkt ihn sich."""
    if _token.get("value") and _token["expires_at"] > time.time() + 60:
        return _token["value"]
    client_id = os.getenv("EBAY_CLIENT_ID", "").strip()
    credentials = f"{client_id}:{os.getenv('EBAY_CLIENT_SECRET', '').strip()}"
    with _http() as client:
        response = client.post(
            _url(TOKEN_URL),
            headers={"Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": SCOPE},
        )
    if response.status_code != 200:
        # eBays eigener Grund (z.B. "client authentication failed") – enthält keine Schlüssel
        try:
            reason = response.json().get("error_description") or response.json().get("error")
        except ValueError:
            reason = None
        detail = (tr("eBay sagt: {reason}", reason=str(reason)[:150]) if reason
                  else f"Status {response.status_code}")
        raise ProductSourceError(tr("eBay-Anmeldung fehlgeschlagen – stimmen EBAY_CLIENT_ID und "
                                    "EBAY_CLIENT_SECRET in .env? (Production-Keys, Keyset nicht "
                                    "gesperrt?) {detail}", detail=detail))
    data = response.json()
    _token.update(value=data["access_token"], expires_at=time.time() + data.get("expires_in", 7200))
    return _token["value"]


def large_image(url: str) -> str:
    """eBay-Bilder gibt es in mehreren Größen (…/s-l225.jpg). Größer = bessere Bilderkennung."""
    return re.sub(r"/s-l\d+\.(jpg|jpeg|png|webp)$", r"/s-l500.\1", url)


# --- Suche und Umwandlung in Produkte ---------------------------------------------------------

def search(query: str) -> list[dict]:
    """Eine Suche auf eBay (nur Sofort-Kaufen) – gleiche Suchen aller Personen teilen sich
    eine Stunde lang ein Ergebnis (search_cache.py)."""
    here = region.current()
    key = (f"ebay|{here.ebay}|{here.currency}|{os.getenv('EBAY_EPN_CAMPAIGN_ID', '').strip()}|"
           f"{RESULTS_PER_QUERY}|{query}")      # mehr Treffer pro Suche -> neu fragen
    return search_cache.cached(key, lambda: _search(query))


def _search(query: str) -> list[dict]:
    params = {"q": query, "limit": RESULTS_PER_QUERY,
              "filter": f"buyingOptions:{{FIXED_PRICE}},price:[{MIN_PRICE}..],"
                        f"priceCurrency:{region.current().currency}"}
    headers = {
        "Authorization": f"Bearer {app_token()}",
        # Marktplatz des Landes der Person (region.py): ebay.at, ebay.com, ebay.co.uk …
        "X-EBAY-C-MARKETPLACE-ID": region.current().ebay,
    }
    campaign = os.getenv("EBAY_EPN_CAMPAIGN_ID", "").strip()
    if campaign:  # eBay liefert dann Partnerlinks mit (itemAffiliateWebUrl)
        headers["X-EBAY-C-ENDUSERCTX"] = f"affiliateCampaignId={campaign}"
    with _http() as client:
        response = client.get(_url(SEARCH_URL), params=params, headers=headers)
    if response.status_code != 200:
        raise ProductSourceError(tr("eBay-Suche fehlgeschlagen ({code}).", code=response.status_code))
    return [{k: item[k] for k in KEEP_FIELDS if k in item}
            for item in response.json().get("itemSummaries", [])]


def to_product(item: dict, department: str, query_category: str) -> Product | None:
    """eBay-Ergebnis -> Product. None, wenn wichtige Angaben fehlen."""
    try:
        price = float(item["price"]["value"])
        currency = item["price"].get("currency", region.current().currency)
        image = (item.get("image") or {}).get("imageUrl") or \
            (item.get("thumbnailImages") or [{}])[0].get("imageUrl")
        # Partnerlink, falls eBay einen geliefert hat – sonst der normale Link
        url = item.get("itemAffiliateWebUrl") or item["itemWebUrl"]
        sponsored = "itemAffiliateWebUrl" in item
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    title = item.get("title", "")
    if not image or not url.startswith("https://") or currency != region.current().currency \
            or JUNK_PATTERN.search(title):
        return None

    # Kategorie aus dem Titel – passt sie nicht zur Welt, die der Suche
    categories = [c for c in find_terms(title, CATEGORY_PATTERNS)
                  if CATEGORY_SYNONYMS[c][0] == department]
    condition = item.get("condition", "")
    second_hand = bool(condition) and not condition.lower().startswith(("neu", "new"))
    category = categories[0] if categories else query_category
    # Gemeinsame Regeln (quality.py) – gebraucht darf günstig sein
    if quality.rejected(title, "", department, price, currency, category, min_price=not second_hand):
        return None
    return Product(
        id="ebay-" + re.sub(r"[^A-Za-z0-9]", "-", item["itemId"]),
        name=title[:90],
        shop="eBay · Second Hand" if second_hand else "eBay",
        seller=str((item.get("seller") or {}).get("username") or ""),
        price=price,
        # Sale: eBay liefert den Preis vor der Reduzierung mit (marketingPrice)
        original_price=sale_price(price, ((item.get("marketingPrice") or {})
                                          .get("originalPrice") or {}).get("value")),
        currency=currency,
        department=department,
        category=category,
        gender=gender_of(title) if department == "mode" else None,
        colors=sorted(find_terms(title, COLOR_PATTERNS)),
        style_tags=sorted(find_terms(title, STYLE_PATTERNS)),
        image_url=large_image(image),
        affiliate_url=url,
        sponsored=sponsored,  # nur mit Partnerlink ist es Werbung
    )


class EbayProductSource(CachedSource):
    """Produktquelle mit echten eBay-Angeboten, passend zum Stilprofil der Pins."""

    name = "ebay"
    cache_file = "ebay_cache.json"

    def fetch(self) -> list[Product]:
        return self.fetch_for(storage.load_pins()["pins"], DEPARTMENTS)

    def fetch_for(self, pins: list[dict], departments, keep=None) -> list[Product]:
        """Suche passend zu beliebigen Pins (auch zu einem hochgeladenen Foto).
        keep(query, category) -> False überspringt eine Suche."""
        planned = [(department, query) for department in departments
                   for query in build_queries(pins, department, search_words(), QUERIES)
                   if not keep or keep(query[0], query[1])]
        # Alle Suchen gleichzeitig – sonst wartet der Shop über eine Minute
        results = run_parallel(lambda job: search_with_fallback(search, job[1]), planned)
        products, seen = [], set()
        for (department, (_, category)), found in zip(planned, results):
            for item in found:
                product = to_product(item, department, category)
                if product and product.id not in seen:
                    seen.add(product.id)
                    products.append(product)
        return products


def main() -> None:
    """Prüft eBay Schritt für Schritt:  python -m backend.ebay
    Zeigt pro Suche, wie viele Angebote eBay liefert und wie viele davon übrig bleiben."""
    from backend import config  # noqa: F401  (lädt .env)
    if not configured():
        print("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET fehlen in .env.")
        return
    marketplace = region.current().ebay
    print(f"Server: {'SANDBOX (nur Testdaten!)' if sandbox() else 'Production'} | Marktplatz: {marketplace}")
    try:
        app_token()
    except ProductSourceError as err:
        print(err)
        return
    print("Anmeldung: ok")
    pins = storage.load_pins()["pins"]
    queries = [(q, d) for d in DEPARTMENTS for q in build_queries(pins, d, search_words(), QUERIES)]
    if not queries:
        print("Keine Pins gefunden – teste mit einem Beispiel.")
        queries = [(("schwarze Hose", "Hosen"), "mode")]
    total = 0
    for planned, department in queries:
        query, category = planned
        items = search_with_fallback(search, planned)
        kept = [p for p in (to_product(i, department, category) for i in items) if p]
        total += len(kept)
        print(f"  {query:<40} eBay: {len(items):>2}  übrig: {len(kept):>2}")
        fallback = getattr(planned, "fallback", None)
        if fallback:
            print(f"    (zu wenig? dann auch: {fallback})")
        if items and not kept:
            first = items[0]
            print(f"    z.B. {first.get('title', '')[:50]!r} | Preis: {first.get('price')}")
    print(f"\nZusammen: {total} Angebote.")


def support_report() -> str:
    """Bericht für den eBay-Support: Anfrage + genaue Antwort beim Token-Holen.
    Enthält die App ID, aber NIE das Secret (Cert ID) und keinen Token."""
    import datetime
    import json
    client_id = os.getenv("EBAY_CLIENT_ID", "").strip()
    credentials = f"{client_id}:{os.getenv('EBAY_CLIENT_SECRET', '').strip()}"
    with _http() as client:
        response = client.post(
            _url(TOKEN_URL),
            headers={"Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": SCOPE},
        )
    try:
        body = json.dumps(response.json(), indent=2)
    except ValueError:
        body = response.text[:2000]
    if response.status_code == 200:
        body = "(token received – not included)"
    useful = ["date", "x-ebay-c-request-id", "rlogid", "x-ebay-request-id", "content-type"]
    headers = "\n".join(f"  {k}: {v}" for k, v in response.headers.items() if k.lower() in useful)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""eBay OAuth application token – diagnostic report
Created: {now}

App ID (Client ID): {client_id}
Environment:        {"Sandbox" if sandbox() else "Production"}
Marketplace:        {region.current().ebay}

REQUEST
  POST {_url(TOKEN_URL)}
  Authorization: Basic <base64(App ID:Cert ID) – removed>
  Content-Type: application/x-www-form-urlencoded
  grant_type=client_credentials
  scope={SCOPE}

RESPONSE
  HTTP {response.status_code}
{headers}

{body}

Use case: Browse API (buy/browse/v1/item_summary/search), public listings only.
No eBay user data is requested or stored.
"""


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        from pathlib import Path

        from backend import config  # noqa: F401  (lädt .env)
        out = Path("ebay-support-report.txt")
        out.write_text(support_report(), "utf-8")
        print(f"Bericht gespeichert: {out.resolve()}  (enthält kein Secret)")
    else:
        main()
