"""Tests: ähnliche Artikel ("Mehr wie das") und die Detailseite.

Starten mit:  pytest -v
"""

from backend import storage
from backend.similar import jaccard, similar_products, similarity
from tests.test_products import make_product


def test_jaccard():
    assert jaccard(["beige", "weiß"], ["beige"]) == 0.5
    assert jaccard(["beige"], ["beige"]) == 1.0
    assert jaccard(["beige"], ["schwarz"]) == 0.0
    assert jaccard([], ["beige"]) == 0.0


def test_different_departments_are_never_similar():
    hoodie = make_product(department="mode", category="Oberteile", colors=["beige"])
    vase = make_product(department="wohnen", category="Deko", colors=["beige"])
    assert similarity(hoodie, vase) == 0.0


def test_most_similar_first_and_self_excluded():
    hoodie = make_product(id="hoodie", category="Oberteile", colors=["beige"],
                          style_tags=["oversized", "streetwear"])
    candidates = [
        hoodie,
        make_product(id="hose-schwarz", category="Hosen", colors=["schwarz"], style_tags=["elegant"]),
        make_product(id="shirt-street", category="Oberteile", colors=["schwarz"],
                     style_tags=["streetwear", "oversized"]),
        make_product(id="pulli-beige", category="Oberteile", colors=["beige"],
                     style_tags=["oversized", "streetwear"], price=30),
        make_product(id="vase", department="wohnen", category="Deko", colors=["beige"]),
    ]
    result = similar_products(hoodie, candidates)
    ids = [r["id"] for r in result]
    assert ids == ["pulli-beige", "shirt-street"]   # nichts Fremdes, nicht sich selbst
    assert result[0]["shared"] == ["beige", "oversized", "streetwear"]


def test_ties_cheaper_first_and_limit():
    base = make_product(id="base", category="Hosen", colors=["blau"])
    candidates = [make_product(id=f"h{i}", category="Hosen", colors=["blau"], price=50 - i)
                  for i in range(5)]
    result = similar_products(base, candidates, limit=3)
    assert [r["price"] for r in result] == [46, 47, 48]


# --- API --------------------------------------------------------------------------------------

def test_api_product_detail(fake, client):
    data = client.get("/api/products/prod-001").json()   # Oversized Hoodie Sand
    assert data["product"]["name"] == "Oversized Hoodie Sand"
    assert data["has_profile"] is False
    assert 0 < len(data["similar"]) <= 12
    assert all(p["department"] == "mode" for p in data["similar"])
    assert "prod-001" not in [p["id"] for p in data["similar"]]
    # Das ähnlichste ist ein anderes Oberteil
    assert data["similar"][0]["category"] == "Oberteile"


def test_api_product_detail_uses_profile_for_reason(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        {"id": "1", "title": "Ceramic vase", "description": "beige japandi"}]})
    data = client.get("/api/products/prod-031").json()   # Keramikvase Sand
    assert data["has_profile"] is True
    assert data["product"]["reason"].startswith("Passt zu dir")
    assert all(p["department"] == "wohnen" for p in data["similar"])


def test_api_product_detail_errors(fake, client):
    assert client.get("/api/products/gibtsnicht").status_code == 404
    assert client.get("/api/products/prod-001?limit=0").status_code == 422
    assert len(client.get("/api/products/prod-001?limit=3").json()["similar"]) == 3


def test_detail_page_exists(client):
    assert client.get("/produkt.html").status_code == 200
    assert client.get("/produkt.js").status_code == 200
