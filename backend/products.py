"""Schritt 4: Produktdaten.

Der Rest der App fragt Produkte nur über get_product_source() ab und weiß nicht,
woher sie kommen. Heute aus data/products.json, später z.B. aus einem
Affiliate-Feed (CSV/XML eines Partnernetzwerks). Dafür schreibst du eine neue
Klasse, die von ProductSource erbt, und gibst sie in get_product_source() zurück.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from backend.config import BASE_DIR

PRODUCTS_FILE = BASE_DIR / "data" / "products.json"


class Product(BaseModel):
    """So sieht ein Produkt aus. Pydantic prüft beim Laden jedes Feld."""
    id: str
    name: str
    shop: str
    price: float = Field(ge=0)        # ge=0: Preis darf nicht negativ sein
    currency: str = "EUR"
    category: str
    colors: list[str] = []            # feste Begriffe wie "beige", "schwarz"
    style_tags: list[str] = []        # feste Begriffe wie "streetwear", "oversized"
    image_url: str
    affiliate_url: str


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


def get_product_source() -> ProductSource:
    """HIER wird entschieden, woher die Produkte kommen. Später z.B.:
    return AffiliateFeedSource(url=get_setting("AFFILIATE_FEED_URL"))
    """
    return JsonProductSource()


def filter_products(products: list[Product], min_price: float | None = None,
                    max_price: float | None = None,
                    category: str | None = None) -> list[Product]:
    """Behält nur Produkte im Budget und (optional) in einer Kategorie."""
    result = []
    for product in products:
        if min_price is not None and product.price < min_price:
            continue
        if max_price is not None and product.price > max_price:
            continue
        if category and product.category != category:
            continue
        result.append(product)
    return result


def list_categories(products: list[Product]) -> list[str]:
    """Alle vorkommenden Kategorien, alphabetisch sortiert (für den Filter)."""
    return sorted({product.category for product in products})
