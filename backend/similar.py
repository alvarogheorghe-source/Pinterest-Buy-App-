"""Ähnliche Artikel finden ("Mehr wie das" – wie bei Pinterest).

Zwei Produkte sind ähnlich, wenn sie zur selben Welt gehören und sich Kategorie,
Farben und Stile überschneiden. Wurden Bild-Vektoren berechnet (vision.py), zählt
zusätzlich, wie ähnlich die Bilder AUSSEHEN.
"""

from backend.products import Product
from backend.vision import VISUAL_HINT_THRESHOLD, VISUAL_WEIGHT, cosine, visual_score

# Wie viel zählt was? (zum Ausprobieren und Anpassen)
CATEGORY_WEIGHT = 2.0   # gleiche Kategorie (Hoodie <-> Pullover sind beide "Oberteile")
STYLE_WEIGHT = 2.0      # Stile wie streetwear, japandi
COLOR_WEIGHT = 1.5      # Farben wie beige, schwarz


def jaccard(a: list[str], b: list[str]) -> float:
    """Überschneidung zweier Listen von 0.0 (nichts gemeinsam) bis 1.0 (gleich).

    Gemeinsame Begriffe geteilt durch alle Begriffe:
    ["beige", "weiß"] und ["beige"] -> 1 gemeinsam / 2 insgesamt = 0.5
    """
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(a: Product, b: Product) -> float:
    """Punkte für die Ähnlichkeit zweier Produkte. 0 = gar nicht ähnlich."""
    if a.department != b.department:
        return 0.0  # Kleidung und Gegenstände nie mischen
    score = 0.0
    if a.category == b.category:
        score += CATEGORY_WEIGHT
    score += STYLE_WEIGHT * jaccard(a.style_tags, b.style_tags)
    score += COLOR_WEIGHT * jaccard(a.colors, b.colors)
    return score


def similar_products(product: Product, candidates: list[Product], limit: int = 12,
                     vectors: dict[str, list[float]] | None = None) -> list[dict]:
    """Die ähnlichsten Produkte, ähnlichste zuerst (bei Gleichstand günstigere zuerst).

    Jedes Ergebnis enthält "shared": die gemeinsamen Farben und Stile
    (für den Hinweis "Auch beige · oversized").

    vectors (optional, aus vision.py): Bild-Vektoren pro Produkt-ID. Wenn vorhanden,
    zählt zusätzlich, wie ähnlich die BILDER aussehen.
    """
    vectors = vectors or {}
    own_vector = vectors.get(product.id)
    results = []
    for other in candidates:
        if other.id == product.id:
            continue
        if other.department != product.department:
            continue  # Kleidung und Gegenstände nie mischen
        score = similarity(product, other)
        looks = 0.0
        if own_vector and other.id in vectors:
            # Sieht gleich aus, auch ohne gemeinsame Wörter -> zählt trotzdem
            looks = visual_score(cosine(own_vector, vectors[other.id]))
            score += VISUAL_WEIGHT * looks
        if score <= 0:
            continue
        shared = [t for t in other.colors + other.style_tags
                  if t in product.colors or t in product.style_tags]
        results.append({
            **other.model_dump(),
            "similarity": round(score, 3),
            "shared": shared,
            "looks_similar": looks >= VISUAL_HINT_THRESHOLD,
        })
    results.sort(key=lambda r: (-r["similarity"], r["price"]))
    return results[:limit]
