"""Malipin Picks – von uns geprüfte Verkäufer und Teile.

Du trägst sie selbst auf der Admin-Seite ein (/admin.html, Passwort ADMIN_PASSWORD in .env).
Im Shop erscheinen sie wie alle Produkte nach Stil sortiert – mit Abzeichen
"Malipin Pick – von uns geprüft", kleinem Vorrang bei gleichem Stil und eigenem Filter.

Gespeichert in data/picks.json (für alle gleich, nicht persönlich).

Prüf-Kriterien (Vorschlag, siehe Admin-Seite): keine Logos/Markennamen, gute Bewertungen,
Versand in die EU, echte Fotos, Rückgabe möglich.
"""

import secrets
import time

from pydantic import BaseModel, Field, field_validator

from backend import storage
from backend.counterfeit import looks_like_fake
from backend.matching import CATEGORY_SYNONYMS, COLOR_PATTERNS, STYLE_PATTERNS, find_terms
from backend.products import Department, Product, ProductSource

PICKS_FILE = "picks.json"
PICK_BONUS = 0.25   # kleiner Vorrang – nur wenn der Pick überhaupt zum Stil passt


class PickInput(BaseModel):
    """Was du auf der Admin-Seite einträgst."""
    name: str = Field(min_length=2, max_length=120)
    seller: str = Field(min_length=1, max_length=80)
    price: float = Field(ge=0, le=100000)
    department: Department
    category: str
    url: str
    image_url: str
    note: str = Field(default="", max_length=400)      # warum geprüft / was besonders ist
    colors: list[str] = []                             # leer -> automatisch aus Name + Notiz
    style_tags: list[str] = []
    sponsored: bool = False                            # Partnerlink? -> "Werbung"

    @field_validator("url", "image_url")
    @classmethod
    def https_only(cls, url: str) -> str:
        if not url.startswith("https://"):
            raise ValueError("Bitte einen https://-Link")
        return url

    @field_validator("category")
    @classmethod
    def known_category(cls, category: str) -> str:
        if category not in CATEGORY_SYNONYMS:
            raise ValueError("Unbekannte Kategorie")
        return category


def load() -> list[Product]:
    return [Product(**p) for p in storage.read_json(PICKS_FILE, default=[])]


def _save(picks: list[Product]) -> None:
    storage.write_json(PICKS_FILE, [p.model_dump() for p in picks])


def to_product(data: PickInput, pick_id: str) -> Product:
    if CATEGORY_SYNONYMS[data.category][0] != data.department:
        raise ValueError("Kategorie passt nicht zur Welt (Mode/Wohnen)")
    if looks_like_fake(data.name):
        # Der Fälschungs-Filter gilt auch für Picks – Markennamen im Titel nur bei Originalen
        raise ValueError("Der Name enthält eine Marke oder ein Fake-Wort – bei Picks nur "
                         "markenlose Teile (oder das Original direkt beim Markenshop).")
    text = f"{data.name} {data.note}"
    return Product(
        id=pick_id,
        name=data.name,
        shop=f"Malipin Pick · {data.seller}",
        price=round(data.price, 2),
        department=data.department,
        category=data.category,
        colors=data.colors or sorted(find_terms(text, COLOR_PATTERNS)),
        style_tags=data.style_tags or sorted(find_terms(text, STYLE_PATTERNS)),
        image_url=data.image_url,
        affiliate_url=data.url,
        sponsored=data.sponsored,
        pick=True,
        pick_note=data.note,
        pick_added=time.time(),
    )


def add(data: PickInput) -> Product:
    product = to_product(data, "pick-" + secrets.token_hex(4))
    _save(load() + [product])
    return product


def update(pick_id: str, data: PickInput) -> Product | None:
    picks = load()
    for i, old in enumerate(picks):
        if old.id == pick_id:
            picks[i] = to_product(data, pick_id).model_copy(update={"pick_added": old.pick_added})
            _save(picks)
            return picks[i]
    return None


def remove(pick_id: str) -> bool:
    picks = load()
    kept = [p for p in picks if p.id != pick_id]
    _save(kept)
    return len(kept) < len(picks)


class PicksSource(ProductSource):
    def load(self) -> list[Product]:
        return load()


def apply_bonus(ranked: list[dict]) -> list[dict]:
    """Picks, die zum Stil passen (Punkte > 0), rutschen ein Stück nach oben."""
    for item in ranked:
        if item.get("pick") and item["score"] > 0:
            item["score"] = round(item["score"] + PICK_BONUS, 3)
    ranked.sort(key=lambda r: (-r["score"], r["price"]))
    return ranked
