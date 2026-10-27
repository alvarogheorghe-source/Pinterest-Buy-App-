"""Produkt-Feeds von Affiliate-Netzwerken (Awin, Tradedoubler, Adcell, Admitad, CJ …).

Ein Feed ist eine große Datei (CSV oder XML) mit allen Produkten eines Shops: Name, Preis,
Bild, Partnerlink … Dieser Importer liest beliebig viele Feeds ein und macht daraus ganz
normale Malipin-Produkte – Stil-Erkennung, Schnitt & Details, Budgetfilter, Geprüfte Shops
und Fälschungs-Filter funktionieren dann automatisch auch dafür.

Neuer Shop / neues Netzwerk = ein Eintrag in feeds.json (Vorlage: feeds.example.json),
KEIN neuer Code:

    {"name": "awin-mode",                  # kurz, a-z 0-9 -  (wird Teil der Produkt-ID)
     "label": "Awin",                       # Anzeige im Shop
     "preset": "awin",                      # Spalten-Zuordnung: awin, google oder generic
     "url": "https://productdata.awin.com/datafeed/download/apikey/{AWIN_FEED_KEY}/…",
     "countries": ["AT", "DE"],             # Lieferländer (für später: Land pro Person)
     "currencies": ["EUR"],                 # nur diese Währungen übernehmen
     "department": null,                    # "mode"/"wohnen" – null = aus Kategorie erkennen
     "counterfeit_filter": false,           # true bei Marktplätzen mit vielen Fakes
     "fields": {}}                          # eigene Spalten-Namen, überschreibt das Preset

Geheime Schlüssel stehen NIE in feeds.json, sondern in .env – in der URL als {NAME}.

Importieren:  python -m backend.feeds          (lädt alle Feeds neu, zeigt eine Übersicht)
Automatisch:  Sind die Daten älter als FEED_MAX_AGE, lädt die App sie im Hintergrund neu.
"""

import csv
import gzip
import io
import json
import logging
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from backend import storage
from backend import quality
from backend.config import BASE_DIR
from backend.counterfeit import looks_like_fake
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, find_terms, gender_of)
from backend.products import Product, ProductSource, ProductSourceError, sale_price

logger = logging.getLogger(__name__)

CONFIG_FILE = BASE_DIR / "feeds.json"
STORE_FILE = "feed_products.json"           # für alle gleich (storage.GLOBAL_FILES)
# Erhöhen, wenn sich die Erkennung ändert (Kategorien, Damen/Herren, Filter …) – dann lädt die
# App die Feeds von selbst neu, statt alte Ergebnisse zu zeigen
RECOGNITION_VERSION = 5
FEED_MAX_AGE = 24 * 60 * 60                 # Feeds einmal am Tag neu laden
MAX_PER_FEED = 5000                         # mehr braucht kein Shop-Fenster
MAX_DOWNLOAD = 300 * 1024 * 1024            # 300 MB – große Feeds sind oft gepackt (.gz)
MIN_PRICE = 3.0

# Welche Spalte ist was? Pro Netzwerk unterschiedlich. Mehrere Namen = der erste vorhandene.
PRESETS = {
    # Awin "Create-a-Feed" (CSV, oft .gz)
    "awin": {
        "id": ["aw_product_id", "merchant_product_id"], "name": ["product_name"],
        "url": ["aw_deep_link"], "image": ["merchant_image_url", "aw_image_url",
                                           "large_image"],
        "price": ["search_price", "store_price"], "currency": ["currency"],
        "shop": ["merchant_name"], "brand": ["brand_name"],
        "category": ["merchant_category", "category_name"], "color": ["colour"],
        "description": ["product_short_description", "description"],
        "original_price": ["rrp_price", "product_price_old", "base_price"],
        "gender": ["Fashion:suitable_for", "suitable_for", "gender"],
    },
    # Google-Shopping-Format – viele Netzwerke (Tradedoubler, Adcell, Admitad …) bieten es an
    "google": {
        "id": ["id", "g:id"], "name": ["title", "g:title"], "url": ["link", "g:link"],
        "image": ["image_link", "g:image_link"], "price": ["sale_price", "price", "g:price"],
        "currency": [], "shop": ["merchant", "store", "brand", "g:brand"],
        "brand": ["brand", "g:brand"],
        "category": ["product_type", "g:product_type", "google_product_category"],
        "color": ["color", "g:color"], "description": ["description", "g:description"],
        "original_price": ["price", "g:price"],     # Normalpreis, wenn es einen sale_price gibt
        "gender": ["gender", "g:gender"],
    },
    # Allgemein: gängige Spaltennamen; alles andere über "fields" in feeds.json
    "generic": {
        "id": ["id", "product_id", "sku", "ProductID"], "name": ["name", "title", "product_name"],
        "url": ["url", "deeplink", "deep_link", "link", "productUrl", "TrackingUrl"],
        "image": ["image", "image_url", "imageUrl", "picture", "ImageUrl"],
        "price": ["price", "Price", "sale_price"], "currency": ["currency", "Currency",
                                                                "currencyId"],
        "shop": ["merchant", "merchantName", "shop", "store", "vendor"],
        "brand": ["brand", "vendor", "manufacturer"],
        "category": ["category", "categories", "category_path", "merchantCategoryName"],
        "color": ["color", "colour"], "description": ["description", "short_description"],
        "original_price": ["old_price", "original_price", "rrp", "list_price", "regular_price"],
        "gender": ["gender", "Gender", "suitable_for"],
    },
}


class FeedError(Exception):
    pass


# --- Einstellungen ------------------------------------------------------------------------------

def load_config(path: Path | None = None) -> list[dict]:
    path = path or CONFIG_FILE
    if not path.exists():
        return []
    feeds = json.loads(path.read_text("utf-8"))
    for feed in feeds:
        if not re.fullmatch(r"[a-z0-9-]{2,30}", feed.get("name", "")):
            raise FeedError(f"Ungültiger Feed-Name {feed.get('name')!r} (nur a-z, 0-9, -)")
        if feed.get("preset", "generic") not in PRESETS:
            raise FeedError(f"Unbekanntes Preset {feed['preset']!r} – erlaubt: {', '.join(PRESETS)}")
    return feeds


def configured() -> bool:
    try:
        return bool(load_config()) or bool(os.getenv("AWIN_FEED_KEY", "").strip())
    except (FeedError, ValueError):
        return False


# --- Awin automatisch: jeder Shop, der dich annimmt, kommt von selbst dazu ----------------------
# Awin listet alle Produkt-Feeds der Shops, bei denen du angenommen bist (CSV). Daraus werden
# Feeds wie in feeds.json – mit dem Shopnamen als Anzeige. Ausschalten: AWIN_AUTO_FEEDS=0
AWIN_LIST_URL = "https://productdata.awin.com/datafeed/list/apikey/{key}"
# Wohin Shops mit diesem Hauptland üblicherweise auch liefern
NEIGHBOURS = {"DE": ["DE", "AT", "CH"], "AT": ["AT", "DE", "CH"], "CH": ["CH", "DE", "AT"],
              "GB": ["GB", "IE"], "IE": ["IE", "GB"], "US": ["US", "CA"], "CA": ["CA", "US"],
              "AU": ["AU"]}
# EU-Binnenmarkt: Shops aus anderen EU-Ländern (PL, NL, FR …) liefern meist in die ganze EU
EU = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE",
      "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]
# Weltweite Shops: egal welches Awin-Land, sie liefern überallhin
WORLDWIDE = re.compile(r"aliexpress|temu|shein", re.I)


def awin_countries(region: str, name: str) -> list[str]:
    """Wo ein Awin-Shop gezeigt wird ([] = überall)."""
    if WORLDWIDE.search(name):
        return []
    if region in NEIGHBOURS:
        return NEIGHBOURS[region]
    if region in EU:
        return EU
    return [region] if re.fullmatch(r"[A-Z]{2}", region) else []
_AWIN_COLUMNS = {   # mögliche Spaltennamen der Liste (Groß/klein egal)
    "url": ["url", "feed url", "download url"],
    "feed_id": ["feed id", "feed_id", "fid"],
    "name": ["advertiser name", "advertiser", "merchant name"],
    "status": ["membership status", "status", "relationship"],
    "region": ["primary region", "region", "country"],
    "sector": ["vertical", "sector", "category"],
    "products": ["no of products", "number of products", "products"],
}


def _column(row: dict, key: str) -> str:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    return next((str(lower[c]).strip() for c in _AWIN_COLUMNS[key] if lower.get(c)), "")


def _joined(status: str) -> bool:
    """Nur angenommene Shops: "notjoined", "pending", "suspended" … zählen nicht (leer = ja)."""
    status = status.lower()
    return not status or (
        not any(word in status for word in ("not", "pending", "reject", "suspend", "pause",
                                            "inactive", "declin"))
        and any(word in status for word in ("active", "joined", "approved", "member")))


def discover_awin() -> list[dict]:
    """Feeds aller Awin-Shops, die dich angenommen haben. Ohne AWIN_FEED_KEY: keine."""
    key = os.getenv("AWIN_FEED_KEY", "").strip()
    if not key or os.getenv("AWIN_AUTO_FEEDS", "").strip() == "0":
        return []
    found = []
    for row in read_rows(download(AWIN_LIST_URL.format(key=key))):
        url, feed_id = _column(row, "url"), re.sub(r"\D", "", _column(row, "feed_id"))
        if not url.startswith("http") or not feed_id or not _joined(_column(row, "status")):
            continue
        region = _column(row, "region").upper()
        found.append({
            "name": f"awin-{feed_id}", "label": _column(row, "name") or "Awin", "preset": "awin",
            # Awins "Hauptland" ist keine Lieferbeschränkung: deutsche Shops liefern meist auch
            # nach Österreich/Schweiz, britische nach Irland. Deshalb die ganze Nachbarschaft.
            "url": url, "countries": awin_countries(region, _column(row, "name")),
            "currencies": [],                         # jede Währung – wird umgerechnet
        })
    return found


# --- Kandidaten: bei welchen Awin-Shops lohnt sich eine Bewerbung? -----------------------------
# Dieselbe Liste enthält auch Shops, die dich (noch) nicht angenommen haben. Bekannte Marken
# zuerst, dann nach Anzahl Produkte. Nur Shops MIT Feed – ohne Feed zeigt Malipin nichts.
FAMOUS = [
    # Mode
    "zalando", "about you", "otto", "bonprix", "asos", "h&m", "mango", "zara", "breuninger",
    "peek & cloppenburg", "p&c", "na-kd", "snipes", "adidas", "nike", "puma", "reebok",
    "new balance", "converse", "vans", "levi", "tommy hilfiger", "calvin klein", "hugo boss",
    "s.oliver", "esprit", "tom tailor", "marc o'polo", "jack wolfskin", "the north face",
    "timberland", "ugg", "dr. martens", "deichmann", "mytheresa", "farfetch", "net-a-porter",
    "ssense", "shein", "uniqlo", "arket", "& other stories", "weekday", "monki",
    "urban outfitters", "river island", "marks & spencer", "john lewis", "selfridges",
    "harrods", "boohoo", "prettylittlething", "superdry", "jd sports", "foot locker",
    "schuh", "kurt geiger", "pandora", "swarovski", "thomas sabo", "fossil",
    "daniel wellington", "ray-ban", "armedangels", "hessnatur", "lascana", "about you",
    "vestiaire", "momox", "vinted", "lounge by zalando", "nordstrom", "macy's", "revolve",
    "abercrombie", "hollister", "gap", "guess", "lacoste", "ralph lauren", "michael kors",
    "birkenstock", "skechers", "crocs", "the outnet", "matchesfashion", "zalando lounge",
    # Wohnen & Deko
    "westwing", "home24", "maisons du monde", "connox", "lampenwelt", "butlers", "desenio",
    "wayfair", "depot", "ikea", "xxxlutz", "mömax", "poco", "segmüller", "höffner",
    "urbanara", "bloomingville", "ferm living", "nordic nest", "ambientedirect",
    "finnish design shop", "la redoute", "west elm", "pottery barn", "crate & barrel",
    "anthropologie", "dunelm", "habitat", "oliver bonas", "loaf", "cox & cox",
    "the white company", "zara home", "kave home", "sklum", "vidaxl", "beliani", "emma",
    "made.com", "h&m home", "bettenrid", "lumizil", "pib", "junique", "posterlounge",
]
_FAMOUS = re.compile(r"(?<![\w])(" + "|".join(re.escape(b) for b in FAMOUS) + r")(?![\w])")
# Passt zu Malipin (Mode oder Wohnen) – Awins Branche oder der Feed-Name
_RELEVANT = re.compile(
    r"fashion|cloth|apparel|shoe|footwear|accessor|jewel|bag|lingerie|underwear|sport|"
    r"home|garden|furnitur|furnish|decor|interior|living|textile|kitchen|light|mode|"
    r"bekleidung|schuh|möbel|wohnen", re.I)


def awin_candidates(everything: bool = False) -> list[dict]:
    """Noch nicht beigetretene Awin-Shops mit Produkt-Feed, bekannte Marken zuerst."""
    key = os.getenv("AWIN_FEED_KEY", "").strip()
    if not key:
        return []
    shops: dict[str, dict] = {}
    for row in read_rows(download(AWIN_LIST_URL.format(key=key))):
        status = _column(row, "status").lower()
        name = _column(row, "name")
        if not name or _joined(status):
            continue
        sector = _column(row, "sector")
        if not everything and sector and not _RELEVANT.search(f"{sector} {name}"):
            continue
        shop = shops.setdefault(name.lower(), {
            "name": name, "regions": set(), "sector": sector, "products": 0,
            "pending": "pending" in status, "famous": bool(_FAMOUS.search(name.lower()))})
        shop["regions"].add(_column(row, "region").upper() or "?")
        shop["products"] += int(re.sub(r"\D", "", _column(row, "products")) or 0)
    found = sorted(shops.values(), key=lambda s: (not s["famous"], -s["products"], s["name"].lower()))
    return [{**s, "regions": sorted(s["regions"])} for s in found]


def print_candidates(everything: bool = False, limit: int = 150) -> None:
    found = awin_candidates(everything)
    todo = [s for s in found if not s["pending"]]
    print(f"{len(todo)} Awin-Shops mit Feed, bei denen du dich noch bewerben kannst "
          f"({len(found) - len(todo)} schon beworben). ★ = bekannte Marke\n")
    for shop in todo[:limit]:
        star = "★" if shop["famous"] else " "
        count = f"{shop['products']:,}".replace(",", ".")
        print(f" {star} {shop['name'][:32]:<32} {' '.join(shop['regions'])[:12]:<12} "
              f"{shop['sector'][:22]:<22} {count:>8} Produkte")
    if len(todo) > limit:
        print(f"\n… und {len(todo) - limit} weitere (alle: --anzahl 0)")
    print("\nBewerben: Awin -> Advertisers -> Join Programmes -> Namen suchen -> Join")


def all_feeds() -> list[dict]:
    """feeds.json + automatisch gefundene Awin-Feeds (ohne doppelte Namen)."""
    feeds = load_config()
    names = {feed["name"] for feed in feeds}
    return feeds + [feed for feed in discover_awin() if feed["name"] not in names]


def known_feeds() -> list[dict]:
    """Alle Feeds mit Namen und Anzeige – ohne Download (für Admin-Seite & Geprüfte Shops)."""
    feeds = load_config()
    names = {feed["name"] for feed in feeds}
    stored = (storage.read_json(STORE_FILE, default={}) or {}).get("feeds") or {}
    return feeds + [{"name": name, "label": info.get("label", name)}
                    for name, info in stored.items() if name not in names]


def resolve_url(url: str) -> str:
    """"…/apikey/{AWIN_FEED_KEY}/…" -> Schlüssel aus .env einsetzen. Fehlt er: klare Meldung."""
    def value(match):
        name = match.group(1)
        found = os.getenv(name, "").strip()
        if not found:
            raise FeedError(f"{name} fehlt in .env (wird in einer Feed-Adresse gebraucht).")
        return found
    return re.sub(r"\{([A-Z0-9_]+)\}", value, url)


# --- Herunterladen und lesen ------------------------------------------------------------------

def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests Feeds simulieren können."""
    return httpx.Client(timeout=120, follow_redirects=True)


def download(url: str) -> bytes:
    chunks, size = [], 0
    with _http() as client, client.stream("GET", resolve_url(url)) as response:
        if response.status_code != 200:
            raise FeedError(f"Feed nicht abrufbar ({response.status_code}).")
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise FeedError("Feed ist zu groß (über 300 MB).")
            chunks.append(chunk)
    data = b"".join(chunks)
    if data[:2] == b"\x1f\x8b":                       # gepackt (.gz)
        data = gzip.decompress(data)
    return data


def _local_name(tag: str) -> str:
    """"{http://base.google.com/ns/1.0}price" -> "g:price" (so heißen die Spalten im Preset)."""
    if tag.startswith("{"):
        namespace, name = tag[1:].split("}", 1)
        return f"g:{name}" if "google.com" in namespace else name
    return tag


def read_rows(data: bytes):
    """CSV oder XML -> Zeilen als dict (Spaltenname -> Text). Liest Stück für Stück."""
    head = data[:2000].lstrip()
    if head.startswith(b"<"):
        for _, element in ET.iterparse(io.BytesIO(data)):
            if _local_name(element.tag) in ("item", "entry", "product", "offer"):
                yield {_local_name(child.tag): (child.text or "").strip() for child in element}
                element.clear()
        return
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;|\t")
    except csv.Error:
        dialect = csv.excel
    # newline="": Zeilenumbrüche in Feldern (\r, \r\n – z.B. in Beschreibungen) richtig lesen
    yield from csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)


# --- Zeile -> Produkt ---------------------------------------------------------------------------

def _pick(row: dict, names: list[str]) -> str:
    return next((str(row[n]).strip() for n in names if row.get(n) not in (None, "")), "")


def parse_price(text: str) -> tuple[float | None, str | None]:
    """"12,99 EUR" / "EUR 12.99" / "1.299,00" / "12.99" -> (12.99, "EUR")"""
    currency = re.search(r"\b([A-Z]{3})\b", text or "")
    number = re.search(r"\d[\d.,]*", text or "")
    if not number:
        return None, None
    raw = number.group(0).rstrip(".,")
    if "," in raw and "." in raw:          # 1.299,00 oder 1,299.00 -> letztes Zeichen = Komma?
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") \
            else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw), currency.group(1) if currency else None
    except ValueError:
        return None, None


def _https(url: str) -> str:
    return "https://" + url[7:] if url.startswith("http://") else url


def to_product(row: dict, feed: dict) -> Product | None:
    """Eine Feed-Zeile -> Product. None, wenn etwas Wichtiges fehlt oder es nicht passt."""
    fields = {**PRESETS[feed.get("preset", "generic")],
              **{k: v if isinstance(v, list) else [v] for k, v in feed.get("fields", {}).items()}}
    name = _pick(row, fields["name"])
    raw_id = _pick(row, fields["id"])
    url, image = _https(_pick(row, fields["url"])), _https(_pick(row, fields["image"]))
    price, found_currency = parse_price(_pick(row, fields["price"]))
    currency = (_pick(row, fields["currency"]) or found_currency or "EUR").upper()
    if not (name and raw_id and price and url.startswith("https://") and image.startswith("https://")):
        return None
    allowed = feed.get("currencies", ["EUR"])          # leer = jede Währung (wird umgerechnet)
    if price < MIN_PRICE or (allowed and currency not in allowed):
        return None
    if feed.get("counterfeit_filter") and looks_like_fake(name):
        return None

    # Welt + Kategorie: aus der Feed-Kategorie und dem Namen (gleiche Wörter wie bei Pins)
    category_text = _pick(row, fields["category"])
    found = find_terms(f"{category_text} {name}", CATEGORY_PATTERNS)
    wanted = feed.get("department")
    categories = [c for c in sorted(found) if not wanted or CATEGORY_SYNONYMS[c][0] == wanted]
    # Kategorie aus dem Namen hat Vorrang ("Hoodie" in "Mode > Damen > Oberteile > Hoodies")
    from_name = [c for c in categories if c in find_terms(name, CATEGORY_PATTERNS)]
    category = (from_name or categories or [None])[0]
    if not category:
        return None                          # weder Mode noch Wohnen erkennbar -> weglassen
    department = CATEGORY_SYNONYMS[category][0]
    if quality.rejected(name, category_text, department, price, currency, category):
        return None
    if department == "mode" and re.search(r"aliexpress", f"{feed.get('label', '')} {feed['name']}", re.I):
        return None                          # AliExpress nur für Wohnen & Deko (aliexpress.py)

    text = f"{name} {_pick(row, fields['color'])} {_pick(row, fields['description'])[:300]}"
    shop = _pick(row, fields["shop"]) or feed.get("label") or feed["name"]
    return Product(
        id=f"{feed['name']}-{re.sub(r'[^A-Za-z0-9]', '-', raw_id)[:60]}",
        name=name[:90], shop=shop[:60], seller=shop[:60],
        price=round(price, 2), currency=currency,
        original_price=sale_price(price, parse_price(_pick(row, fields["original_price"]))[0]),
        department=department, category=category,
        gender=gender_of(_pick(row, fields.get("gender", [])), category_text, name)
        if department == "mode" else None,
        colors=sorted(find_terms(text, COLOR_PATTERNS)),
        style_tags=sorted(find_terms(text, STYLE_PATTERNS)),
        image_url=image, affiliate_url=url,
        sponsored=True,                       # Feeds kommen immer über Partnerprogramme
        countries=[c.upper() for c in feed.get("countries", [])],
    )


# --- Importieren und speichern ----------------------------------------------------------------

def import_feed(feed: dict) -> dict:
    """Einen Feed laden -> {"products": [...], "rows": n, "kept": n}"""
    products, seen, rows = [], set(), 0
    for row in read_rows(download(feed["url"])):
        rows += 1
        product = to_product(row, feed)
        # Größen/Varianten haben eigene IDs, aber denselben Namen -> nur einmal zeigen
        variant = (product.shop.lower(), re.sub(r"\W+", " ", product.name.lower()).strip()) if product else None
        if product and product.id not in seen and variant not in seen:
            seen.update((product.id, variant))
            products.append(product)
            if len(products) >= feed.get("max_products", MAX_PER_FEED):
                break
    return {"products": products, "rows": rows, "kept": len(products)}


def _without_keys(text: str) -> str:
    """Fehlermeldungen können Adressen enthalten – geheime Schlüssel nie speichern oder zeigen."""
    for name in ("AWIN_FEED_KEY",):
        key = os.getenv(name, "").strip()
        if key:
            text = text.replace(key, "***")
    return text


def import_all(feeds: list[dict] | None = None) -> dict:
    """Alle Feeds neu laden. Fällt einer aus, bleiben seine alten Produkte erhalten."""
    old = storage.read_json(STORE_FILE, default={}) or {}
    if feeds is None:
        try:
            feeds = all_feeds()
        except (FeedError, httpx.HTTPError, csv.Error) as err:   # Awin-Liste nicht abrufbar
            logger.warning("Awin-Feedliste nicht abrufbar: %s", err)
            feeds = load_config() + [{"name": name, "label": info.get("label", name), "url": ""}
                                     for name, info in (old.get("feeds") or {}).items()
                                     if name.startswith("awin-")]
    result = {"fetched_at": time.time(), "version": RECOGNITION_VERSION, "feeds": {}}
    for feed in feeds:
        try:
            if not feed.get("url"):
                raise FeedError("keine Feed-Adresse (Awin-Liste gerade nicht abrufbar)")
            imported = import_feed(feed)
            result["feeds"][feed["name"]] = {
                "label": feed.get("label", feed["name"]), "countries": feed.get("countries", []),
                "rows": imported["rows"], "kept": imported["kept"], "error": None,
                "products": [p.model_dump() for p in imported["products"]]}
        except (FeedError, httpx.HTTPError, ET.ParseError, csv.Error) as err:
            message = _without_keys(str(err))
            logger.warning("Feed %s fällt aus: %s", feed["name"], message)
            previous = (old.get("feeds") or {}).get(feed["name"], {})
            result["feeds"][feed["name"]] = {**previous, "error": message[:200],
                                             "products": previous.get("products", [])}
    storage.write_json(STORE_FILE, result)
    return result


_import_lock = threading.Lock()


def refresh_in_background() -> None:
    """Veraltete Feeds im Hintergrund neu laden – nie zwei Importe gleichzeitig."""
    if not _import_lock.acquire(blocking=False):
        return

    def run():
        try:
            import_all()
        except Exception as err:   # Hintergrund: nie die App stören
            logger.warning("Feed-Import fehlgeschlagen: %s", err)
        finally:
            _import_lock.release()
    threading.Thread(target=run, daemon=True).start()


_memory: dict = {"mtime": None, "products": []}


def stored_products() -> list[Product]:
    """Alle importierten Produkte – im Speicher gehalten, bis sich die Datei ändert."""
    path = storage.DATA_DIR / STORE_FILE
    mtime = path.stat().st_mtime if path.exists() else None
    if mtime != _memory["mtime"]:
        data = storage.read_json(STORE_FILE, default={}) or {}
        _memory.update(mtime=mtime, products=[
            Product(**p) for feed in (data.get("feeds") or {}).values()
            for p in feed.get("products", [])])
    return _memory["products"]


class FeedProductSource(ProductSource):
    """Produkte aus allen Feeds in feeds.json (für alle Personen gleich)."""

    name = "feeds"

    def load(self) -> list[Product]:
        data = storage.read_json(STORE_FILE, default=None)
        if not data:
            # Allererster Start: einmal sofort importieren, damit der Shop nicht leer ist
            try:
                data = import_all()
            except FeedError as err:
                raise ProductSourceError(f"Produkt-Feeds: {err}") from err
        elif (data.get("fetched_at", 0) < time.time() - FEED_MAX_AGE
              or data.get("version") != RECOGNITION_VERSION):
            refresh_in_background()
        products = stored_products()
        if not products and any(f.get("error") for f in (data.get("feeds") or {}).values()):
            errors = [f"{name}: {f['error']}" for name, f in data["feeds"].items() if f.get("error")]
            raise ProductSourceError("Produkt-Feeds nicht abrufbar – " + "; ".join(errors))
        return products

    def fetch_for(self, pins: list[dict], departments, keep=None) -> list[Product]:
        """Für die Foto-Suche: Feed-Produkte der passenden Welt/Kategorie (keine neue Anfrage)."""
        return [p for p in self.load() if p.department in departments
                and (not keep or keep("", p.category))]


def main() -> None:
    import argparse
    from backend import config  # noqa: F401  (lädt .env)
    parser = argparse.ArgumentParser(description="Produkt-Feeds laden")
    parser.add_argument("--kandidaten", action="store_true",
                        help="Awin-Shops mit Feed zeigen, bei denen du dich bewerben kannst")
    parser.add_argument("--alle", action="store_true", help="mit --kandidaten: alle Branchen")
    parser.add_argument("--anzahl", type=int, default=150, help="mit --kandidaten: wie viele (0 = alle)")
    args = parser.parse_args()
    if args.kandidaten:
        if not os.getenv("AWIN_FEED_KEY", "").strip():
            print("AWIN_FEED_KEY fehlt in .env (Awin -> Toolbox -> Create-a-Feed).")
            return
        try:
            print_candidates(args.alle, args.anzahl or 10**9)
        except Exception as error:  # noqa: BLE001
            print(f"Awin-Liste nicht ladbar: {_without_keys(str(error))}")
        return
    if not configured():
        print("Keine Feeds: AWIN_FEED_KEY in .env eintragen (alle angenommenen Awin-Shops kommen dann "
              "automatisch) oder feeds.example.json -> feeds.json kopieren.")
        return
    print("Lade alle Feeds (feeds.json + angenommene Awin-Shops) …\n")
    result = import_all()
    if not result["feeds"]:
        print("Noch keine Feeds – bei Awin bist du wohl noch bei keinem Shop angenommen.")
    total = 0
    for name, feed in result["feeds"].items():
        if feed.get("error"):
            print(f"  ✗ {name:<20} Fehler: {feed['error']}")
            continue
        total += feed["kept"]
        print(f"  ✓ {feed.get('label', name)[:28]:<28} {feed['rows']:>6} Zeilen -> "
              f"{feed['kept']:>5} passende Produkte")
    print(f"\nZusammen: {total} Produkte im Shop.")


if __name__ == "__main__":
    main()
