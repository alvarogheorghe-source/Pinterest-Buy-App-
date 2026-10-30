"""Warum findet die Foto-Suche nichts? Zeigt jeden Schritt von photo.recommend mit Zahlen.

Aufruf (am Server):  .venv/bin/python -m scripts.photo_check <bild-datei-oder-url>
Ohne Argument wird das Bild des ersten Feed-Produkts genommen (sollte sich selbst finden).
"""

import sys
from collections import Counter

import httpx

from backend import config  # noqa: F401  (lädt .env)
from backend import photo, vision
from backend.matching import build_style_profile, rank_products
from backend.products import online_sources


def load_bytes(arg: str | None) -> bytes:
    if arg and not arg.startswith("http"):
        return open(arg, "rb").read()
    if not arg:
        from backend.feeds import FeedProductSource
        first = next(p for p in FeedProductSource().load() if p.image_url)
        print(f"Testbild: {first.name[:60]}")
        arg = first.image_url
    return httpx.get(arg, follow_redirects=True, timeout=20).content


def main() -> None:
    data = load_bytes(sys.argv[1] if len(sys.argv) > 1 else None)
    print("Quellen:", [type(s).__name__ for s in online_sources()] or "keine (Beispielkatalog)")
    embedder = vision.get_embedder()
    store = vision.EmbeddingStore(embedder.name)
    print("Gespeicherte Bild-Vektoren:", sum(1 for k in store.items if k.startswith("product:")))
    vector = embedder.embed_image_bytes([data])[0]
    pin = photo.photo_pin(data, vector, embedder, store)
    print("Erkannt:", {k: pin[k] for k in ("image_relevant", "image_department",
                                           "image_categories", "image_styles", "image_gender")})
    found = photo.candidates(pin)
    print("Kandidaten:", len(found), Counter(p.category for p in found).most_common(8))
    ranked = rank_products(found, build_style_profile([pin]))
    if pin["image_categories"]:
        same = [r for r in ranked if r["category"] in pin["image_categories"]]
        print("Davon passende Kategorie:", len(same))
        ranked = same or ranked
    top = ranked[:photo.VISUAL_CHECK]
    have = sum(1 for p in top if store.get(f"product:{p['id']}"))
    print(f"Top {len(top)}: {have} mit gespeichertem Bild-Vektor")
    sims = []
    for p in top:
        v = store.get(f"product:{p['id']}")
        sims.append((round(vision.visual_score(vision.cosine(vector, v)), 2) if v else None, p["name"][:50]))
    sims.sort(key=lambda s: -(s[0] or 0))
    print(f"Ähnlichkeit (Grenze {photo.PHOTO_MIN}):")
    for s, name in sims[:10]:
        print(f"  {s}  {name}")
    print("Über der Grenze:", sum(1 for s, _ in sims if s and s >= photo.PHOTO_MIN))


if __name__ == "__main__":
    main()
