"""Foto hochladen → Mali findet's 📷 – ähnliche Teile zu einem eigenen Foto, ohne Pinterest.

Ablauf:
1. Foto prüfen (nur im Arbeitsspeicher – es wird NIE gespeichert)
2. FashionCLIP: Stil, Teile, Herren/Damen, Marke (image_tags.tag) + Hauptfarbe (pin_colors)
3. Daraus ein "Foto-Pin" – damit funktioniert alles wie bei Pins: Suchbegriffe für eBay/Etsy
   (gezielt nur für das, was auf dem Foto ist), sonst der Beispielkatalog
4. Sortieren: erst nach Begriffen, dann vergleicht das Modell die besten Treffer direkt mit
   dem Foto ("sieht genauso aus"); erkannte Marke gibt einen Bonus
"""

import io

from backend import image_tags, pin_colors, vision
from backend.brands import BRANDS
from backend.matching import build_style_profile, classify_pin, color_from_hex, rank_products
from backend.products import (DEPARTMENTS, JsonProductSource, Product, online_sources,
                              remember_photo_results)

MAX_BYTES = 8 * 1024 * 1024
RESULTS = 24          # so viele Produkte zeigen
VISUAL_CHECK = 36     # so viele der Text-Besten vergleicht das Modell direkt mit dem Foto
VISUAL_WEIGHT = 3.0   # beim Foto zählt "sieht genauso aus" mehr als bei vielen Pins
BRAND_BONUS = 1.5


class PhotoError(Exception):
    """Kein brauchbares Bild (falsches Format, zu groß …)."""


def check_image(data: bytes) -> None:
    if not data:
        raise PhotoError("Kein Foto empfangen.")
    if len(data) > MAX_BYTES:
        raise PhotoError("Das Foto ist zu groß (höchstens 8 MB).")
    try:
        from PIL import Image
        Image.open(io.BytesIO(data)).verify()
    except Exception as err:
        raise PhotoError("Das ist kein Bild, das ich lesen kann (JPG, PNG, WebP …).") from err


def photo_pin(data: bytes, vector: list[float], embedder, store) -> dict:
    """Was ist auf dem Foto? -> ein Pin wie aus Pinterest, nur ohne Text."""
    tags = image_tags.tag(vector, image_tags.label_vectors(embedder, store))
    return {
        "id": "photo", "title": "", "description": "",
        "image_styles": tags["styles"], "image_categories": tags["categories"],
        "image_gender": tags["gender"], "image_brands": tags["brands"],
        "image_relevant": tags["relevant"], "image_department": tags["department"],
        "image_seen": tags["seen"],
        "dominant_color": pin_colors.dominant_hex(data),
    }


def candidates(pin: dict) -> list[Product]:
    """Produkte, die zum Foto passen könnten: gezielte Online-Suche oder Beispielkatalog."""
    # Die Vorprüfung weiß, ob Mode oder Wohnen zu sehen ist – sonst wie bei Pins entscheiden
    departments = ([pin["image_department"]] if pin.get("image_department")
                   else [d for d in DEPARTMENTS if d in classify_pin(pin)])
    wanted = set(pin["image_categories"]) | {BRANDS[b].category for b in pin["image_brands"]}
    sources = online_sources()
    if not sources:
        return [p for p in JsonProductSource().load() if p.department in departments]

    # Nur Suchen für das, was auf dem Foto ist (nicht die allgemeinen Standard-Kategorien)
    def keep(query, category):
        return not wanted or category in wanted

    found: list[Product] = []
    for source in sources:
        try:
            found += source.fetch_for([pin], departments, keep=keep)
        except Exception:  # eine Quelle fällt aus -> die anderen reichen
            continue
    remember_photo_results(found)
    return found


def recommend(data: bytes) -> dict:
    """Foto -> {"found": {...was Mali sieht...}, "products": [...ähnliche Teile...]}"""
    check_image(data)
    embedder = vision.get_embedder()       # wirft VisionUnavailable ohne KI-Pakete
    store = vision.EmbeddingStore(embedder.name)
    vector = embedder.embed_image_bytes([data])[0]
    if vector is None:
        raise PhotoError("Das Foto konnte ich nicht öffnen.")

    pin = photo_pin(data, vector, embedder, store)
    if not pin["image_relevant"]:
        # Bildschirm, Essen, Text … -> keine Suche; Mali sagt freundlich, was er stattdessen sieht
        return {"relevant": False, "seen": pin["image_seen"], "found": None, "products": []}
    ranked = rank_products(candidates(pin), build_style_profile([pin]))

    # Die besten Text-Treffer direkt mit dem Foto vergleichen (fehlende Bilder berechnen)
    top = ranked[:VISUAL_CHECK]
    vision.index(store, embedder, [(f"product:{p['id']}", p["image_url"]) for p in top])
    store.save()
    brands = [b.lower() for b in pin["image_brands"]]
    for item in top:
        product_vector = store.get(f"product:{item['id']}")
        similarity = (vision.visual_score(vision.cosine(vector, product_vector))
                      if product_vector else 0.0)
        item["looks_like_photo"] = similarity >= vision.VISUAL_HINT_THRESHOLD
        item["score"] = round(item["score"] + VISUAL_WEIGHT * similarity, 3)
        if any(brand.split()[0] in item["name"].lower() for brand in brands):
            item["score"] += BRAND_BONUS
    top.sort(key=lambda r: (-r["score"], r["price"]))

    color = color_from_hex(pin["dominant_color"])
    return {
        "relevant": True,
        "seen": pin["image_seen"],
        "found": {
            "categories": pin["image_categories"],
            "styles": pin["image_styles"],
            "brands": pin["image_brands"],
            "colors": [color] if color else [],
            "gender": pin["image_gender"],
            "department": pin["image_department"],
        },
        "products": top[:RESULTS],
    }
