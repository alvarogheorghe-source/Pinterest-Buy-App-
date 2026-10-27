"""Geprüfte Shops – Shops und Verkäufer, die wir als sicher einstufen.

Statt einzelne Teile einzutragen, prüfst du einmal einen Shop (Originalware, gute Bewertungen,
EU-Versand, Rückgabe …). Danach bekommen ALLE seine Angebote im Shop automatisch:
- das Abzeichen "Geprüfter Shop"
- einen kleinen Vorrang, wenn sie zum Stil passen (SHOP_BONUS)
- den Filter "Nur geprüfte Shops"
- bei AliExpress: offizielle Markenstores dürfen Markennamen zeigen (sonst Fälschungs-Filter)

Ein Shop = Plattform + Verkäufer, so wie er auf der Plattform heißt:
    eBay        -> Verkäufername (steht auf jeder eBay-Angebotsseite)
    Etsy        -> Shop-Name (etsy.com/shop/<Name>)
    AliExpress  -> Store-Nummer (aliexpress.com/store/<Nummer>)

Eintragen auf der Admin-Seite /admin.html (Passwort ADMIN_PASSWORD in .env).
Gespeichert in data/trusted_shops.json – für alle Besucher gleich.
"""

import secrets
import time
from pydantic import BaseModel, Field, field_validator

from backend import storage
from backend.products import Product

SHOPS_FILE = "trusted_shops.json"
SHOP_BONUS = 0.25    # kleiner Vorrang – nur wenn das Angebot überhaupt zum Stil passt
PLATFORM_NAMES = {"ebay": "eBay", "etsy": "Etsy", "aliexpress": "AliExpress"}
# Plattform = eBay/Etsy/AliExpress oder der Name eines Produkt-Feeds (feeds.json), dort ist
# der "Verkäufer" der Händler im Feed (z.B. "awin-mode" + "Beispiel Store")


class ShopInput(BaseModel):
    """Was du auf der Admin-Seite einträgst."""
    platform: str = Field(pattern=r"^[a-z0-9-]{2,30}$")
    seller: str = Field(min_length=1, max_length=80)     # Verkäufername / Shop-Name / Store-Nr.
    name: str = Field(min_length=1, max_length=80)       # Anzeigename, z.B. "adidas Official Store"
    note: str = Field(default="", max_length=300)        # warum geprüft

    @field_validator("platform")
    @classmethod
    def known_platform(cls, platform: str) -> str:
        from backend import feeds
        try:
            feed_names = {feed["name"] for feed in feeds.known_feeds()}
        except (feeds.FeedError, ValueError):
            feed_names = set()
        if platform not in PLATFORM_NAMES and platform not in feed_names:
            raise ValueError("Unbekannte Plattform – erlaubt: eBay, Etsy, AliExpress oder ein Feed")
        return platform


def _key(platform: str, seller: str) -> tuple[str, str]:
    return platform, seller.strip().lower()


def load() -> list[dict]:
    return storage.read_json(SHOPS_FILE, default=[])


def add(data: ShopInput) -> dict:
    shops = load()
    if any(_key(s["platform"], s["seller"]) == _key(data.platform, data.seller) for s in shops):
        raise ValueError("Dieser Shop ist schon eingetragen.")
    shop = {"id": "shop-" + secrets.token_hex(4), **data.model_dump(), "added": time.time()}
    storage.write_json(SHOPS_FILE, shops + [shop])
    return shop


def remove(shop_id: str) -> bool:
    shops = load()
    kept = [s for s in shops if s["id"] != shop_id]
    storage.write_json(SHOPS_FILE, kept)
    return len(kept) < len(shops)


def platform_of(product: Product) -> str:
    """Plattform aus der Produkt-ID ("ebay-…", "etsy-…", "aliexpress-…")."""
    return product.id.split("-", 1)[0]


def lookup() -> dict[tuple[str, str], dict]:
    return {_key(s["platform"], s["seller"]): s for s in load()}


def is_trusted(platform: str, seller: str, shops: dict | None = None) -> bool:
    shops = lookup() if shops is None else shops
    return bool(seller) and _key(platform, seller) in shops


def mark(products: list[Product]) -> list[Product]:
    """Setzt trusted/trusted_note bei allen Angeboten geprüfter Shops."""
    shops = lookup()
    if not shops:
        return products
    marked = []
    for product in products:
        shop = shops.get(_key(platform_of(product), product.seller)) if product.seller else None
        marked.append(product.model_copy(update={"trusted": True, "trusted_note": shop["note"]})
                      if shop else product)
    return marked


def apply_bonus(ranked: list[dict]) -> list[dict]:
    """Angebote geprüfter Shops, die zum Stil passen (Punkte > 0), rutschen etwas nach oben."""
    for item in ranked:
        if item.get("trusted") and item["score"] > 0:
            item["score"] = round(item["score"] + SHOP_BONUS, 3)
    ranked.sort(key=lambda r: (-r["score"], r["price"]))
    return ranked
