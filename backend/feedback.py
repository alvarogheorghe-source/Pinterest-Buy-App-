"""👍 / 👎 der Nutzer – und wie sie die Vorschläge verändern.

- 👎 (dislike): Produkt wird ausgeblendet, ÄHNLICHE Produkte rutschen nach unten.
- 👍 (like):    ÄHNLICHE Produkte rutschen nach oben.

"Ähnlich" kommt aus similar.py (gleiche Kategorie, Farben, Stile). Die Bewertungen
liegen in data/feedback.json und können später auch als Testdaten dienen:
Was jemand mit 👍 bewertet, ist ein echtes "passt".
"""

import time

from backend import storage
from backend.products import Product
from backend.similar import CATEGORY_WEIGHT, COLOR_WEIGHT, STYLE_WEIGHT, similarity

FEEDBACK_FILE = "feedback.json"
VOTES = ("like", "dislike")

# Höchstmögliche Ähnlichkeit (gleiche Kategorie + gleiche Stile + gleiche Farben)
MAX_SIMILARITY = CATEGORY_WEIGHT + STYLE_WEIGHT + COLOR_WEIGHT

# Wie stark Feedback die Punkte verändert (zum Vergleich: ein Begriff, der in
# JEDEM Pin vorkommt, bringt 1 Punkt)
LIKE_BOOST = 1.0
DISLIKE_PENALTY = 1.0

# Ab dieser Ähnlichkeit (0..1) gilt ein Produkt als "ähnlich wie ein Like"
HINT_THRESHOLD = 0.6


def load_feedback() -> dict[str, dict]:
    """{"prod-001": {"vote": "like", "at": 1730000000.0}, ...}"""
    return storage.read_json(FEEDBACK_FILE, default={})


def set_vote(product_id: str, vote: str | None) -> dict[str, dict]:
    """Speichert eine Bewertung. vote=None löscht sie (z.B. "Rückgängig")."""
    feedback = load_feedback()
    if vote is None:
        feedback.pop(product_id, None)
    else:
        feedback[product_id] = {"vote": vote, "at": time.time()}
    storage.write_json(FEEDBACK_FILE, feedback)
    return feedback


def clear_feedback() -> None:
    storage.delete_json(FEEDBACK_FILE)


def ids_with_vote(feedback: dict[str, dict], vote: str) -> set[str]:
    return {pid for pid, entry in feedback.items() if entry["vote"] == vote}


def closest(product: Product, others: list[Product]) -> float:
    """Ähnlichkeit (0..1) zum ähnlichsten Produkt aus "others"."""
    scores = [similarity(product, other) for other in others if other.id != product.id]
    return max(scores, default=0.0) / MAX_SIMILARITY


def apply_feedback(ranked: list[dict], all_products: list[Product],
                   feedback: dict[str, dict]) -> list[dict]:
    """Nimmt die sortierten Vorschläge aus matching.rank_products() und
    berücksichtigt 👍/👎: Dislikes raus, Punkte anpassen, neu sortieren."""
    by_id = {p.id: p for p in all_products}
    liked = [by_id[pid] for pid in ids_with_vote(feedback, "like") if pid in by_id]
    disliked = [by_id[pid] for pid in ids_with_vote(feedback, "dislike") if pid in by_id]
    liked_ids = {p.id for p in liked}
    disliked_ids = {p.id for p in disliked}

    results = []
    for item in ranked:
        if item["id"] in disliked_ids:
            continue  # 👎 = ausblenden
        product = by_id[item["id"]]
        # Ein selbst gelikter Artikel bekommt den vollen Bonus (closest() überspringt
        # das Produkt selbst, sonst stünde es unter seinen ähnlichen Produkten)
        like_similarity = 1.0 if product.id in liked_ids else closest(product, liked)
        adjustment = LIKE_BOOST * like_similarity - DISLIKE_PENALTY * closest(product, disliked)
        results.append({
            **item,
            "score": round(item["score"] + adjustment, 3),
            "vote": feedback.get(item["id"], {}).get("vote"),
            "feedback_hint": like_similarity >= HINT_THRESHOLD and product.id not in liked_ids,
        })

    results.sort(key=lambda r: (-r["score"], r["price"]))
    return results
