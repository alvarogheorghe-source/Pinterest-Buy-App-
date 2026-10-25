"""Tests für das Messwerkzeug (backend/evaluate.py).

Starten mit:  pytest -v
"""

from backend.evaluate import evaluate, load_testset, text_recommender
from backend.products import JsonProductSource


def test_metrics_with_a_fake_recommender():
    cases = [
        {"id": "a", "department": "mode", "pin": {}, "relevant": ["p1"]},   # Platz 1
        {"id": "b", "department": "mode", "pin": {}, "relevant": ["p3"]},   # Platz 3
        {"id": "c", "department": "mode", "pin": {}, "relevant": ["p9"]},   # nicht gefunden
        {"id": "d", "department": "mode", "pin": {}, "relevant": ["p1"]},   # kein Signal
    ]
    answers = {"a": ["p1", "p2"], "b": ["p1", "p2", "p3"], "c": ["p1"], "d": []}
    rankings = iter(answers[c["id"]] for c in cases)

    report = evaluate(cases, lambda pin, dep, products: next(rankings), products=[])
    assert report["hit_at_1"] == 0.25
    assert report["hit_at_k"] == 0.5
    assert report["avg_rank"] == 2.0          # (1 + 3) / 2
    assert report["no_signal"] == 1
    assert [r["first_hit"] for r in report["cases"]] == [1, 3, None, None]


def test_hits_outside_top_k_do_not_count():
    cases = [{"id": "a", "department": "mode", "pin": {}, "relevant": ["p6"]}]
    report = evaluate(cases, lambda *_: ["p1", "p2", "p3", "p4", "p5", "p6"], [], k=5)
    assert report["hit_at_k"] == 0.0
    assert report["cases"][0]["first_hit"] == 6


def test_demo_testset_is_valid():
    """Jedes "relevant"-Produkt muss existieren und zur angegebenen Welt gehören."""
    products = {p.id: p for p in JsonProductSource().load()}
    cases = load_testset()
    assert len(cases) >= 10
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["relevant"], case["id"]
        for pid in case["relevant"]:
            assert products[pid].department == case["department"], (case["id"], pid)


def test_text_recommender_finds_nothing_without_words():
    products = JsonProductSource().load()
    assert text_recommender({"title": "fit 🤍", "description": ""}, "mode", products) == []
    ranking = text_recommender({"title": "Keramikvase", "description": "sand"}, "wohnen", products)
    assert ranking[0] == "prod-031"
    assert all(pid in {p.id for p in products if p.department == "wohnen"} for pid in ranking)


def test_board_name_and_image_color_help_text_poor_pins():
    """Ohne Board/Farbe kein Signal – mit Board-Name und Bildfarbe ein Ergebnis."""
    from backend.evaluate import pin_text_only_recommender
    products = JsonProductSource().load()
    pin = {"title": "home inspo ✨", "description": "", "board_name": "Balkon",
           "dominant_color": "#c46a43"}
    assert pin_text_only_recommender(pin, "wohnen", products) == []
    assert text_recommender(pin, "wohnen", products)[0] == "prod-041"   # Pflanztopf Terracotta


def test_demo_comparison_board_and_color_not_worse():
    """Wache gegen Rückschritte: Board + Farbe darf auf dem Demo-Set nicht schlechter sein."""
    from backend.evaluate import RECOMMENDERS
    products = JsonProductSource().load()
    cases = load_testset()
    text_only = evaluate(cases, RECOMMENDERS["Nur Pin-Text"], products)
    with_board = evaluate(cases, RECOMMENDERS["Text + Board + Bildfarbe"], products)
    assert with_board["hit_at_k"] >= text_only["hit_at_k"]
    assert with_board["no_signal"] <= text_only["no_signal"]
