"""Schritt 4: Produktdaten.

Der Rest der App fragt Produkte nur über get_product_source() ab und weiß nicht,
woher sie kommen. Heute aus data/products.json, später z.B. aus einem
Affiliate-Feed (CSV/XML eines Partnernetzwerks). Dafür schreibst du eine neue
Klasse, die von ProductSource erbt, und gibst sie in get_product_source() zurück.
"""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.config import BASE_DIR

PRODUCTS_FILE = BASE_DIR / "data" / "products.json"

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


def get_product_source() -> ProductSource:
    """HIER wird entschieden, woher die Produkte kommen:
    - eBay (echte Angebote), wenn EBAY_CLIENT_ID/EBAY_CLIENT_SECRET in .env stehen
    - sonst die Beispielprodukte aus data/products.json
    PRODUCT_SOURCE=demo in .env erzwingt die Beispielprodukte.
    Später kommen weitere Quellen dazu (z.B. ein Awin-Feed).
    """
    from backend import ebay  # erst hier, sonst importieren sich die Dateien gegenseitig
    if os.getenv("PRODUCT_SOURCE", "").strip().lower() != "demo" and ebay.configured():
        return ebay.EbayProductSource()
    return JsonProductSource()


def source_name() -> str:
    """Für die Anzeige im Shop: "ebay" oder "demo"."""
    from backend import ebay
    return "ebay" if isinstance(get_product_source(), ebay.EbayProductSource) else "demo"


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
