"""Tests für 👍/👎 (backend/feedback.py und /api/feedback).

Starten mit:  pytest -v
"""

from backend import feedback
from backend.matching import build_style_profile, rank_products
from tests.test_products import make_product


def products_for_test():
    return [
        make_product(id="hoodie-beige", category="Oberteile", colors=["beige"],
                     style_tags=["oversized", "streetwear"], price=35),
        make_product(id="pulli-beige", category="Oberteile", colors=["beige"],
                     style_tags=["oversized", "cozy"], price=30),
        make_product(id="kleid-schwarz", category="Kleider & Röcke", colors=["schwarz"],
                     style_tags=["elegant"], price=33),
        make_product(id="rock-schwarz", category="Kleider & Röcke", colors=["schwarz"],
                     style_tags=["elegant", "klassisch"], price=29),
    ]


def ranked_without_profile(items):
    return rank_products(items, build_style_profile([]))  # alle Punkte 0 -> nach Preis


def test_dislike_hides_product_and_pushes_similar_down():
    items = products_for_test()
    votes = {"kleid-schwarz": {"vote": "dislike", "at": 0}}
    result = feedback.apply_feedback(ranked_without_profile(items), items, votes)
    ids = [r["id"] for r in result]
    assert "kleid-schwarz" not in ids                 # ausgeblendet
    assert ids[-1] == "rock-schwarz"                  # ähnlicher Rock rutscht ans Ende,
    assert ids[0] == "pulli-beige"                    # obwohl er am günstigsten ist


def test_like_pushes_similar_up_with_hint():
    items = products_for_test()
    votes = {"hoodie-beige": {"vote": "like", "at": 0}}
    result = feedback.apply_feedback(ranked_without_profile(items), items, votes)
    by_id = {r["id"]: r for r in result}
    assert [r["id"] for r in result][:2] == ["hoodie-beige", "pulli-beige"]
    assert by_id["hoodie-beige"]["vote"] == "like"
    assert by_id["pulli-beige"]["feedback_hint"] is True      # "ähnlich wie ein Like"
    assert by_id["hoodie-beige"]["feedback_hint"] is False    # das Like selbst nicht
    assert by_id["rock-schwarz"]["feedback_hint"] is False


def test_no_feedback_changes_nothing():
    items = products_for_test()
    ranked = ranked_without_profile(items)
    result = feedback.apply_feedback(ranked, items, {})
    assert [r["id"] for r in result] == [r["id"] for r in ranked]
    assert all(r["score"] == 0 for r in result)


# --- API ----------------------------------------------------------------------------------------

def test_api_vote_undo_and_reset(fake, client):
    assert client.get("/api/feedback").json() == {}
    assert client.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"}).json() \
        == {"product_id": "prod-001", "vote": "like"}
    assert client.get("/api/feedback").json()["prod-001"]["vote"] == "like"

    client.post("/api/feedback", json={"product_id": "prod-001", "vote": None})  # Rückgängig
    assert client.get("/api/feedback").json() == {}

    client.post("/api/feedback", json={"product_id": "prod-002", "vote": "dislike"})
    client.delete("/api/feedback")
    assert client.get("/api/feedback").json() == {}


def test_api_rejects_bad_votes(fake, client):
    assert client.post("/api/feedback", json={"product_id": "gibtsnicht", "vote": "like"}) \
        .status_code == 404
    assert client.post("/api/feedback", json={"product_id": "prod-001", "vote": "super"}) \
        .status_code == 422


def test_api_recommendations_and_detail_respect_feedback(fake, client):
    client.post("/api/feedback", json={"product_id": "prod-001", "vote": "dislike"})
    client.post("/api/feedback", json={"product_id": "prod-023", "vote": "like"})

    shop = client.get("/api/recommendations?department=mode").json()["products"]
    assert "prod-001" not in [p["id"] for p in shop]
    assert next(p for p in shop if p["id"] == "prod-023")["vote"] == "like"

    detail = client.get("/api/products/prod-005").json()      # Strickpullover Creme
    assert "prod-001" not in [p["id"] for p in detail["similar"]]
    assert len(detail["similar"]) == 12                         # trotzdem volle Liste
    assert client.get("/api/products/prod-023").json()["product"]["vote"] == "like"
