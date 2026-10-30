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

from backend import garments, image_tags, pin_colors, vision
from backend.brands import BRANDS
from backend.matching import build_style_profile, classify_pin, color_from_hex, rank_products
from backend.products import (DEPARTMENTS, JsonProductSource, Product, online_sources,
                              remember_photo_results)

MAX_BYTES = 8 * 1024 * 1024
RESULTS = 8           # höchstens so viele Produkte zeigen (Qualität statt Menge)
PHOTO_MIN = 0.3       # so ähnlich muss ein Produktbild dem Foto mindestens sehen (0..1)
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


def photo_pin(data: bytes, vector: list[float], embedder, store, force: bool = False) -> dict:
    """Was ist auf dem Foto? -> ein Pin wie aus Pinterest, nur ohne Text."""
    tags = image_tags.tag(vector, image_tags.label_vectors(embedder, store), force=force)
    return {
        "id": "photo", "title": "", "description": "",
        "image_styles": tags["styles"], "image_categories": tags["categories"],
        "image_gender": tags["gender"], "image_brands": tags["brands"],
        "image_relevant": tags["relevant"], "image_department": tags["department"],
        "image_seen": tags["seen"],
        "image_details": tags["details"],
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
    return found


def closest(pin: dict, vector: list[float], found: list[Product], embedder, store,
            limit: int, visual_check: int) -> list[dict]:
    """Die Kandidaten, die dem Bild (Vektor) wirklich ähnlich sehen, beste zuerst."""
    ranked = rank_products(found, build_style_profile([pin]))
    # Nur die Kategorie, die auf dem Foto ist (z.B. Jeans), wenn Mali sie erkannt hat
    if pin["image_categories"]:
        ranked = [r for r in ranked if r["category"] in pin["image_categories"]] or ranked

    # Die besten Text-Treffer direkt mit dem Foto vergleichen (fehlende Bilder berechnen).
    # Ein Foto hat keinen Text – darum zusätzlich ALLE Kandidaten, deren Bild schon
    # berechnet ist (nächtliche Bilderkennung): sonst gewinnen nur zufällige Text-Treffer.
    top = ranked[:visual_check]
    vision.index(store, embedder, [(f"product:{p['id']}", p["image_url"]) for p in top])
    top += [r for r in ranked[visual_check:] if store.get(f"product:{r['id']}")]
    brands = [b.lower() for b in pin["image_brands"]]
    for item in top:
        product_vector = store.get(f"product:{item['id']}")
        similarity = (vision.visual_score(vision.cosine(vector, product_vector))
                      if product_vector else 0.0)
        item["similarity"] = similarity
        item["looks_like_photo"] = similarity >= vision.VISUAL_HINT_THRESHOLD
        item["score"] = round(item["score"] + VISUAL_WEIGHT * similarity, 3)
        if any(brand.split()[0] in item["name"].lower() for brand in brands):
            item["score"] += BRAND_BONUS
    # Nur Teile, die dem Foto wirklich ähnlich sehen – lieber wenige als viele
    top = [item for item in top if item.pop("similarity") >= PHOTO_MIN]
    top.sort(key=lambda r: (-r["score"], r["price"]))
    return top[:limit]


def retag_person(pin: dict, data: bytes, pieces: list, embedder, store) -> None:
    """Stil, Damen/Herren, Marke noch einmal auf dem Ausschnitt um die Person bestimmen –
    ohne Hintergrund rät FashionCLIP hier deutlich besser."""
    person = garments.person_crop(data, pieces)
    vector = embedder.embed_image_bytes([person])[0] if person else None
    if vector is None:
        return
    tags = image_tags.tag(vector, image_tags.label_vectors(embedder, store), force=True)
    pin.update(image_styles=tags["styles"] or pin["image_styles"], image_gender=tags["gender"] or pin["image_gender"],
               image_brands=tags["brands"], image_details=tags["details"])


def recommend(data: bytes, force: bool = False) -> dict:
    """Foto -> {"found": {...was Mali sieht...}, "groups": [{Teil, Farbe, Produkte}], "products": [...]}
    force: "Da ist doch ein Fit drauf" -> trotzdem suchen."""
    check_image(data)
    embedder = vision.get_embedder()       # wirft VisionUnavailable ohne KI-Pakete
    store = vision.EmbeddingStore(embedder.name)
    vector = embedder.embed_image_bytes([data])[0]
    if vector is None:
        raise PhotoError("Das Foto konnte ich nicht öffnen.")

    pin = photo_pin(data, vector, embedder, store, force=force)
    if not pin["image_relevant"]:
        # Bildschirm, Essen, Text … -> keine Suche; Mali sagt freundlich, was er stattdessen sieht
        return {"relevant": False, "seen": pin["image_seen"], "found": None, "products": []}

    # Outfit-Foto: einzelne Kleidungsstücke ausschneiden und jedes für sich suchen (garments.py)
    pieces = garments.find(data) if pin["image_department"] != "wohnen" else []
    vectors = embedder.embed_image_bytes([p.crop for p in pieces]) if pieces else []
    looks = [(p, v) for p, v in zip(pieces, vectors) if v is not None]
    if looks:
        retag_person(pin, data, [p for p, _ in looks], embedder, store)
        searches = [({**pin, "image_categories": [p.category], "image_department": "mode",
                      "dominant_color": pin_colors.dominant_hex(p.crop)}, v) for p, v in looks]
    else:
        searches = [(pin, vector)]          # ein einzelnes Teil, Deko … -> ganzes Bild

    per_search = max(3, RESULTS // len(searches))
    groups, shown, everything = [], set(), []
    for search_pin, search_vector in searches:
        found = candidates(search_pin)
        everything += found
        top = [item for item in closest(search_pin, search_vector, found, embedder, store,
                                        per_search, max(12, VISUAL_CHECK // len(searches)))
               if item["id"] not in shown]
        shown |= {item["id"] for item in top}
        color = color_from_hex(search_pin["dominant_color"])
        groups.append({"category": search_pin["image_categories"][0] if looks else None,
                       "color": color, "products": top})
    store.save()
    remember_photo_results([p for p in everything if p.id in shown])

    categories = ([g["category"] for g in groups] if looks else pin["image_categories"])
    colors = list(dict.fromkeys(g["color"] for g in groups if g["color"]))
    return {
        "relevant": True,
        "seen": pin["image_seen"],
        "found": {
            "categories": categories,
            "styles": pin["image_styles"],
            "brands": pin["image_brands"],
            "details": [name for _, name in pin["image_details"]],
            "colors": colors,
            "gender": pin["image_gender"],
            "department": "mode" if looks else pin["image_department"],
        },
        "groups": groups if looks else [],
        "products": [item for g in groups for item in g["products"]],
    }
