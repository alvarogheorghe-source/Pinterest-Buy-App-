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
from backend.config import BASE_DIR
from backend.counterfeit import looks_like_fake
from backend.matching import (CATEGORY_PATTERNS, CATEGORY_SYNONYMS, COLOR_PATTERNS,
                              STYLE_PATTERNS, find_terms)
from backend.products import Product, ProductSource, ProductSourceError, sale_price

logger = logging.getLogger(__name__)

CONFIG_FILE = BASE_DIR / "feeds.json"
STORE_FILE = "feed_products.json"           # für alle gleich (storage.GLOBAL_FILES)
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
        return bool(load_config())
    except (FeedError, ValueError):
        return False


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
    yield from csv.DictReader(io.StringIO(text), dialect=dialect)


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
    if price < MIN_PRICE or currency not in feed.get("currencies", ["EUR"]):
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

    text = f"{name} {_pick(row, fields['color'])} {_pick(row, fields['description'])[:300]}"
    shop = _pick(row, fields["shop"]) or feed.get("label") or feed["name"]
    return Product(
        id=f"{feed['name']}-{re.sub(r'[^A-Za-z0-9]', '-', raw_id)[:60]}",
        name=name[:90], shop=shop[:60], seller=shop[:60],
        price=round(price, 2), currency=currency,
        original_price=sale_price(price, parse_price(_pick(row, fields["original_price"]))[0]),
        department=CATEGORY_SYNONYMS[category][0], category=category,
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
        if product and product.id not in seen:
            seen.add(product.id)
            products.append(product)
            if len(products) >= feed.get("max_products", MAX_PER_FEED):
                break
    return {"products": products, "rows": rows, "kept": len(products)}


def import_all(feeds: list[dict] | None = None) -> dict:
    """Alle Feeds neu laden. Fällt einer aus, bleiben seine alten Produkte erhalten."""
    feeds = load_config() if feeds is None else feeds
    old = storage.read_json(STORE_FILE, default={}) or {}
    result = {"fetched_at": time.time(), "feeds": {}}
    for feed in feeds:
        try:
            imported = import_feed(feed)
            result["feeds"][feed["name"]] = {
                "label": feed.get("label", feed["name"]), "countries": feed.get("countries", []),
                "rows": imported["rows"], "kept": imported["kept"], "error": None,
                "products": [p.model_dump() for p in imported["products"]]}
        except (FeedError, httpx.HTTPError, ET.ParseError, csv.Error) as err:
            logger.warning("Feed %s fällt aus: %s", feed["name"], err)
            previous = (old.get("feeds") or {}).get(feed["name"], {})
            result["feeds"][feed["name"]] = {**previous, "error": str(err)[:200],
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
        elif data.get("fetched_at", 0) < time.time() - FEED_MAX_AGE:
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
    from backend import config  # noqa: F401  (lädt .env)
    feeds = load_config()
    if not feeds:
        print("Keine Feeds eingetragen – Vorlage: feeds.example.json -> feeds.json kopieren.")
        return
    print(f"Lade {len(feeds)} Feed(s) …\n")
    result = import_all(feeds)
    total = 0
    for name, feed in result["feeds"].items():
        if feed.get("error"):
            print(f"  ✗ {name:<20} Fehler: {feed['error']}")
            continue
        total += feed["kept"]
        print(f"  ✓ {name:<20} {feed['rows']:>6} Zeilen -> {feed['kept']:>5} passende Produkte")
    print(f"\nZusammen: {total} Produkte im Shop.")


if __name__ == "__main__":
    main()
