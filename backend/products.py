"""Schritt 4: Produktdaten.

Der Rest der App fragt Produkte nur über get_product_source() ab und weiß nicht,
woher sie kommen. Heute aus data/products.json, später z.B. aus einem
Affiliate-Feed (CSV/XML eines Partnernetzwerks). Dafür schreibst du eine neue
Klasse, die von ProductSource erbt, und gibst sie in get_product_source() zurück.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.config import BASE_DIR

PRODUCTS_FILE = BASE_DIR / "data" / "products.json"
logger = logging.getLogger(__name__)

# Die zwei "Welten" der App: Kleidung und Gegenstände
DEPARTMENTS = ("mode", "wohnen")
Department = Literal["mode", "wohnen"]  # Literal: nur genau diese Werte sind erlaubt


class Product(BaseModel):
    """So sieht ein Produkt aus. Pydantic prüft beim Laden jedes Feld."""
    id: str
    name: str
    shop: str
    price: float = Field(ge=0)        # ge=0: Preis darf nicht negativ sein
    currency: str = "EUR"
    department: Department = "mode"   # "mode" = Kleidung, "wohnen" = Gegenstände
    category: str
    colors: list[str] = []            # feste Begriffe wie "beige", "schwarz"
    style_tags: list[str] = []        # feste Begriffe wie "streetwear", "oversized"
    image_url: str
    affiliate_url: str
    # True = wir verdienen am Link (Affiliate) -> Kennzeichnung "Werbung"
    sponsored: bool = True
    # Malipin Pick: von uns geprüft (backend/picks.py)
    pick: bool = False
    pick_note: str = ""
    pick_added: float | None = None

    @field_validator("affiliate_url")
    @classmethod
    def must_be_web_link(cls, url: str) -> str:
        """Nur echte Web-Links erlauben. Ein "javascript:..."-Link aus einem
        fremden Feed könnte sonst beim Klick Code im Browser ausführen."""
        if not url.startswith(("https://", "http://")):
            raise ValueError("Link muss mit http:// oder https:// beginnen")
        return url

    @field_validator("image_url")
    @classmethod
    def must_be_image_link(cls, url: str) -> str:
        """Web-Link oder ein eigenes Bild der App (z.B. "/img/products/prod-001.png").
        "//andere-seite.com/..." sieht aus wie ein eigener Pfad, führt aber woanders hin."""
        own_image = url.startswith("/") and not url.startswith("//")
        if not (own_image or url.startswith(("https://", "http://"))):
            raise ValueError("Bild muss ein http(s)-Link oder ein eigener Pfad (/img/...) sein")
        return url


class ProductSourceError(Exception):
    """Die Produktdaten konnten nicht geladen werden."""


class ProductSource:
    """Grundgerüst für jede Produktquelle. Jede Quelle muss load() können."""

    def load(self) -> list[Product]:
        raise NotImplementedError


class JsonProductSource(ProductSource):
    """Liest Produkte aus einer JSON-Datei im Format {"products": [...]}."""

    def __init__(self, path: Path = PRODUCTS_FILE):
        self.path = path

    def load(self) -> list[Product]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [Product(**item) for item in raw["products"]]
        except FileNotFoundError:
            raise ProductSourceError(f"Datei nicht gefunden: {self.path}")
        except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as err:
            raise ProductSourceError(f"Fehler in {self.path.name}: {err}")


class CachedSource(ProductSource):
    """Quelle mit Online-Suche (eBay, Etsy, ...). Ergebnisse werden zwischengespeichert,
    damit nicht jeder Klick eine Anfrage kostet. Neue Pins leeren den Speicher."""

    name = ""                    # z.B. "ebay" – für die Anzeige im Shop
    cache_file = ""              # z.B. "ebay_cache.json" (in data/, gitignored)
    cache_seconds = 60 * 60      # 1 Stunde

    def fetch(self) -> list[Product]:
        """Neu suchen. Muss jede Quelle selbst können."""
        raise NotImplementedError

    def load(self) -> list[Product]:
        from backend import storage
        cached = storage.read_json(self.cache_file, default=None)
        if cached and cached.get("fetched_at", 0) > time.time() - self.cache_seconds:
            return [Product(**p) for p in cached["products"]]
        products = self.fetch()
        storage.write_json(self.cache_file, {"fetched_at": time.time(),
                                             "products": [p.model_dump() for p in products]})
        return products


class CombinedSource(ProductSource):
    """Mischt mehrere Quellen (z.B. eBay + Etsy). Fällt eine aus, kommen die anderen
    trotzdem – nur wenn ALLE ausfallen, gibt es eine Fehlermeldung."""

    def __init__(self, sources: list[ProductSource]):
        self.sources = sources

    def load(self) -> list[Product]:
        products, errors, seen = [], [], set()
        for source in self.sources:
            try:
                for product in source.load():
                    if product.id not in seen:      # gleiches Angebot aus zwei Quellen nur einmal
                        seen.add(product.id)
                        products.append(product)
            except ProductSourceError as error:
                errors.append(error)
                logger.warning("Produktquelle %s fällt aus: %s", type(source).__name__, error)
        if errors and len(errors) == len(self.sources):
            raise errors[0]
        return products


PHOTO_RESULTS_FILE = "photo_results.json"
MAX_PHOTO_RESULTS = 200


class PhotoResultsSource(ProductSource):
    """Produkte aus Foto-Suchen (backend/photo.py) – damit ♡, Detailseite und "Mehr wie das"
    auch für sie funktionieren. Gespeichert werden nur die Produkte, NIE das Foto."""

    def load(self) -> list[Product]:
        from backend import storage
        return [Product(**p) for p in storage.read_json(PHOTO_RESULTS_FILE, default=[])]


def remember_photo_results(found: list[Product]) -> None:
    """Neue Foto-Ergebnisse vorne anfügen (höchstens MAX_PHOTO_RESULTS)."""
    from backend import storage
    ids = {p.id for p in found}
    old = [p for p in storage.read_json(PHOTO_RESULTS_FILE, default=[]) if p["id"] not in ids]
    storage.write_json(PHOTO_RESULTS_FILE, ([p.model_dump() for p in found] + old)[:MAX_PHOTO_RESULTS])


def online_sources() -> list[CachedSource]:
    """Alle Online-Quellen, für die Schlüssel in .env stehen."""
    # erst hier, sonst importieren sich die Dateien gegenseitig
    from backend import aliexpress, ebay, etsy
    if os.getenv("PRODUCT_SOURCE", "").strip().lower() == "demo":
        return []
    candidates = [(ebay.configured, ebay.EbayProductSource), (etsy.configured, etsy.EtsyProductSource),
                  (aliexpress.configured, aliexpress.AliExpressProductSource)]
    return [source() for configured, source in candidates if configured()]


def get_product_source() -> ProductSource:
    """HIER wird entschieden, woher die Produkte kommen:
    - echte Angebote von eBay und/oder Etsy, wenn deren Schlüssel in .env stehen
    - sonst die Beispielprodukte aus data/products.json
    PRODUCT_SOURCE=demo in .env erzwingt die Beispielprodukte.
    Später kommen weitere Quellen dazu (z.B. ein Awin-Feed).
    """
    from backend import storage
    from backend import picks
    sources: list[ProductSource] = list(online_sources())
    if sources and storage.exists(PHOTO_RESULTS_FILE):
        sources.append(PhotoResultsSource())
    if not sources:
        sources = [JsonProductSource()]
    if storage.exists(picks.PICKS_FILE):          # Malipin Picks: immer dabei, für alle gleich
        sources.append(picks.PicksSource())
    return sources[0] if len(sources) == 1 else CombinedSource(sources)


def source_names() -> list[str]:
    """Für die Anzeige im Shop: z.B. ["ebay", "etsy"] oder ["demo"]."""
    return [source.name for source in online_sources()] or ["demo"]


def filter_products(products: list[Product], min_price: float | None = None,
                    max_price: float | None = None, category: str | None = None,
                    department: str | None = None) -> list[Product]:
    """Behält nur Produkte im Budget und (optional) in einer Welt/Kategorie."""
    result = []
    for product in products:
        if department and product.department != department:
            continue
        if min_price is not None and product.price < min_price:
            continue
        if max_price is not None and product.price > max_price:
            continue
        if category and product.category != category:
            continue
        result.append(product)
    return result


def list_categories(products: list[Product], department: str | None = None) -> list[str]:
    """Alle vorkommenden Kategorien (optional einer Welt), alphabetisch sortiert."""
    return sorted({p.category for p in products if not department or p.department == department})
