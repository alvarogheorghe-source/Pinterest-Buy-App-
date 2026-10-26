"""Schnitt & Details (backend/details.py): genauere Suchen und genaueres Ranking."""

from backend import details
from backend.matching import build_style_profile, rank_products
from backend.search_queries import ENGLISH, Query, build_queries, search_with_fallback
from tests.test_products import make_product


def pins(*titles):
    return [{"id": str(i), "title": t} for i, t in enumerate(titles)]


def test_finds_several_details_per_part():
    found = details.find("High waist light wash bootcut jeans, cropped top", ["Hosen", "Oberteile"])
    assert {("Hosen", "Bootcut"), ("Hosen", "Light Wash"), ("Hosen", "High Waist"),
            ("Hosen", "Jeans"), ("Oberteile", "Cropped")} <= found
    assert ("Oberteile", "Bootcut") not in found          # Bootcut gibt es nur bei Hosen
    assert details.find("gestreifte Bluse", ["Oberteile"]) >= {("Oberteile", "Gestreift")}
    assert details.find("bootcut", []) == set()            # ohne erkanntes Teil nichts


def test_profile_counts_details_per_category():
    profile = build_style_profile(pins("baggy jeans", "baggy light wash jeans", "black hoodie"),
                                  "mode")
    assert set(profile.top_details("Hosen")[:2]) == {("Baggy", 2), ("Jeans", 2)}
    assert profile.to_dict()["details"]["Hosen"]["Light Wash"] == 1


def test_queries_use_exact_part_and_details():
    board = pins("light wash baggy jeans", "baggy jeans light wash", "brown suede chelsea boots",
                 "brown suede chelsea boots")
    queries = build_queries(board, "mode")
    texts = [q for q, _ in queries]
    assert "Baggy Light Wash Jeans" in texts or "Light Wash Baggy Jeans" in texts   # keine Farbe dazu
    assert "braun Wildleder Chelsea Boots" in texts           # genaues Teil statt "Sneaker"
    jeans = next(q for q in queries if "Jeans" in q[0])
    assert jeans.fallback == "Jeans"                          # Sicherheitsnetz
    assert "suede chelsea boots" in " ".join(q for q, _ in build_queries(board, "mode", ENGLISH))


def test_no_contradicting_words():
    queries = [q for q, _ in build_queries(pins("black cargo pants", "black cargo pants"), "mode")]
    assert "schwarz Cargohose" in queries                     # nicht "Cargo Cargohose"
    queries = [q for q, _ in build_queries(pins("oversized chunky sneakers") * 2, "mode")]
    assert not any("oversized" in q and "Sneaker" in q for q in queries)


def test_fallback_search_only_when_too_few():
    calls = []

    def search(text):
        calls.append(text)
        return [{"id": i} for i in range(2 if text == "Bootcut Jeans" else 10)]

    assert len(search_with_fallback(search, Query("Bootcut Jeans", "Hosen", "Jeans"))) == 12
    assert calls == ["Bootcut Jeans", "Jeans"]
    calls.clear()
    search_with_fallback(search, Query("Jeans", "Hosen", "Jeans"))   # gleich -> kein Netz
    assert calls == ["Jeans"]


def test_ranking_prefers_pinned_fit_and_punishes_the_opposite():
    profile = build_style_profile(pins("bootcut jeans", "bootcut jeans", "bootcut jeans"), "mode")
    bootcut = make_product(id="p1", name="Levis Bootcut Jeans blau", category="Hosen", price=40)
    plain = make_product(id="p2", name="Jeans blau", category="Hosen", price=30)
    skinny = make_product(id="p3", name="Skinny Jeans blau", category="Hosen", price=20)
    ranked = rank_products([skinny, plain, bootcut], profile)
    assert [r["id"] for r in ranked] == ["p1", "p2", "p3"]
    assert ranked[0]["matched"][0] in ("Bootcut", "Jeans")
    assert "Bootcut" in ranked[0]["reason"] or "Jeans" in ranked[0]["reason"]
