"""Bild-Prüfung pro Produkt: KI-Bild? Für Damen oder Herren? (FashionCLIP, Zero-Shot)

Wie image_tags.py bei den Pins: Wir vergleichen das Produktbild mit Beschreibungen und
schauen, welche besser passt.

- KI-Bilder, Renderings und Fantasie-Mockups (oft bei Etsy) zerstören den Vibe -> raus.
  Bewusst vorsichtig (AI_MIN): lieber ein KI-Bild übersehen als echte Fotos aussortieren.
- Damen/Herren aus dem Bild, wenn der Titel nichts verrät (z.B. "Pants Modell: Kenny").

Läuft automatisch mit:              python -m backend.vision
Aussortierte Bilder ansehen:        python -m backend.product_checks
Ergebnis: data/product_checks.json  {"etsy-123": {"ai": 0.91, "gender": "damen"}, …}
"""

from backend import storage
from backend.image_tags import label_vectors, softmax
from backend.vision import cosine, mean_direction

CHECKS_FILE = "product_checks.json"

# Echtes Foto oder künstlich? Mehrere Sätze pro Seite, gemittelt (wie TEMPLATES in image_tags)
PHOTO_PROMPTS = {
    "real": ["a real product photo taken with a camera", "a model wearing clothes in a photo shoot",
             "a product photo on a plain background", "a real photo of a room interior",
             "a flat lay photo of clothing"],
    "ai": ["an AI generated image", "a digital illustration", "a 3D render",
           "a computer generated fake photo", "a surreal digital artwork",
           "an unrealistic glossy AI picture"],
}
AI_MIN = 0.85        # erst ab 85 % "künstlich" aussortieren
GENDER_MIN = 0.85    # Produktfotos ohne Person sind oft unklar -> strenger als bei Pins (0.70)


def photo_vectors(embedder, store) -> dict[str, list[float]]:
    """Ein Vektor für "echt" und einer für "künstlich" – einmal berechnet, dann gespeichert."""
    found = {}
    for key, texts in PHOTO_PROMPTS.items():
        label, url = f"label:photo:{key}", " | ".join(texts)
        vector = store.get(label, url)
        if vector is None:
            vector = mean_direction(embedder.embed_texts(texts))
            store.put(label, url, vector)
        found[key] = vector
    return found


def check(vector: list[float], photo: dict, gender: dict) -> dict:
    """{"ai": Wahrscheinlichkeit künstlich, "gender": "damen"/"herren"/None}"""
    ai = softmax({key: cosine(vector, v) for key, v in photo.items()})["ai"]
    genders = softmax({key: cosine(vector, v) for key, v in gender.items()})
    best = max(genders, key=genders.get)
    return {"ai": round(ai, 3), "gender": best if genders[best] >= GENDER_MIN else None}


def run(embedder, store, products) -> dict:
    """Alle Produkte mit Bild-Vektor prüfen und speichern."""
    labels = label_vectors(embedder, store)
    gender = {"herren": labels["gender:herren"], "damen": labels["gender:damen"]}
    photo = photo_vectors(embedder, store)
    results = {}
    for product in products:
        vector = store.get(f"product:{product.id}", product.image_url)
        if vector:
            result = check(vector, photo, gender)
            if product.department != "mode":
                result["gender"] = None
            results[product.id] = result
    storage.write_json(CHECKS_FILE, results)
    return results


_memory: dict = {"mtime": None, "checks": {}}


def load() -> dict:
    """Gespeicherte Prüfungen (im Speicher, bis sich die Datei ändert). Leer = noch nie gelaufen."""
    path = storage.DATA_DIR / CHECKS_FILE
    mtime = path.stat().st_mtime if path.exists() else None
    if mtime != _memory["mtime"]:
        _memory.update(mtime=mtime, checks=storage.read_json(CHECKS_FILE, default={}) or {})
    return _memory["checks"]


def is_ai(product_id: str) -> bool:
    return load().get(product_id, {}).get("ai", 0) >= AI_MIN


def image_gender(product_id: str) -> str | None:
    return load().get(product_id, {}).get("gender")


def main() -> None:
    """Zeigt die aussortierten KI-Bilder – zum Kontrollieren (Link öffnen und anschauen)."""
    from backend.products import get_product_source
    checks = load()
    if not checks:
        print("Noch keine Prüfung – zuerst ausführen:  python -m backend.vision")
        return
    flagged = [p for p in get_product_source().load() if is_ai(p.id)]
    for product in flagged:
        print(f"  {checks[product.id]['ai']:.0%}  {product.shop[:18]:<18} {product.name[:50]:<50} "
              f"{product.image_url}")
    print(f"\n{len(flagged)} von {len(checks)} Produkten sehen nach KI aus und werden nicht gezeigt.")
    print(f"Zu streng oder zu locker? AI_MIN in backend/product_checks.py (jetzt {AI_MIN:.0%}).")


if __name__ == "__main__":
    main()
