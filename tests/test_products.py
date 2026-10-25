"""Tests für Schritt 4: Produktdaten, Produktquelle und Filter.

Starten mit:  pytest -v
"""

import json

import pytest

from backend import products
from backend.products import JsonProductSource, Product, ProductSource, ProductSourceError


def make_product(**changes) -> Product:
    data = {"id": "x1", "name": "Test", "shop": "Testshop", "price": 20.0,
            "category": "Hosen", "image_url": "https://example.com/img.jpg", "affiliate_url": "https://example.com"}
    data.update(changes)
    return Product(**data)


# --- Die mitgelieferte Beispieldatei --------------------------------------------------

def test_example_file_has_50_valid_products():
    items = JsonProductSource().load()  # wirft einen Fehler, falls ein Produkt ungültig ist
    assert len(items) == 50
    assert len({p.id for p in items}) == 50  # alle IDs eindeutig
    assert sum(p.department == "mode" for p in items) == 30
    assert sum(p.department == "wohnen" for p in items) == 20


def test_unknown_department_is_rejected():
    with pytest.raises(ValueError):
        make_product(department="auto")


def test_example_tags_are_lowercase_and_links_are_placeholders():
    for p in JsonProductSource().load():
        assert p.colors and p.style_tags
        assert all(tag == tag.lower() for tag in p.colors + p.style_tags)
        assert p.affiliate_url.startswith("https://example.com/")  # noch kein echter Link


# --- Fehler beim Laden ------------------------------------------------------------------

def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(ProductSourceError, match="nicht gefunden"):
        JsonProductSource(tmp_path / "gibtsnicht.json").load()


def test_invalid_product_gives_clear_error(tmp_path):
    path = tmp_path / "products.json"
    path.write_text(json.dumps({"products": [{"id": "x1", "name": "Ohne Preis"}]}))
    with pytest.raises(ProductSourceError, match="price"):
        JsonProductSource(path).load()


def test_negative_price_is_rejected():
    with pytest.raises(ValueError):
        make_product(price=-5)


def test_dangerous_links_are_rejected():
    with pytest.raises(ValueError, match="http"):
        make_product(affiliate_url="javascript:alert('hack')")
    with pytest.raises(ValueError, match="http"):
        make_product(image_url="data:text/html,<script>")


# --- Filter --------------------------------------------------------------------------------

def test_filter_by_budget_and_category():
    items = [make_product(id="a", price=9.99, category="Hosen"),
             make_product(id="b", price=30.0, category="Hosen"),
             make_product(id="c", price=30.0, category="Schuhe"),
             make_product(id="d", price=80.0, category="Hosen")]

    def ids(result):
        return [p.id for p in result]

    assert ids(products.filter_products(items, max_price=30)) == ["a", "b", "c"]
    assert ids(products.filter_products(items, min_price=20, max_price=50)) == ["b", "c"]
    assert ids(products.filter_products(items, category="Hosen")) == ["a", "b", "d"]
    assert ids(products.filter_products(items, max_price=30, category="Schuhe")) == ["c"]
    assert ids(products.filter_products(items)) == ["a", "b", "c", "d"]


# --- API ----------------------------------------------------------------------------------

def test_api_products_with_filter(client):
    result = client.get("/api/products?max_price=20&category=Accessoires").json()
    assert result  # die Beispieldaten haben günstige Accessoires
    assert all(p["price"] <= 20 and p["category"] == "Accessoires" for p in result)


def test_api_categories_per_department(client):
    assert client.get("/api/categories?department=mode").json() == [
        "Accessoires", "Hosen", "Jacken", "Kleider & Röcke", "Oberteile", "Schuhe"]
    assert client.get("/api/categories?department=wohnen").json() == [
        "Deko", "Küche & Tisch", "Leuchten", "Möbel", "Pflanzen & Töpfe", "Textilien",
        "Wandgestaltung"]
    assert len(client.get("/api/categories").json()) == 13


def test_api_products_by_department(client):
    home = client.get("/api/products?department=wohnen").json()
    assert len(home) == 20 and all(p["department"] == "wohnen" for p in home)
    assert client.get("/api/products?department=auto").status_code == 422  # ungültig


def test_product_source_can_be_swapped(client, monkeypatch):
    """So würde später ein echter Affiliate-Feed eingebunden: eigene Quelle, Rest bleibt gleich."""
    class FakeFeed(ProductSource):
        def load(self):
            return [make_product(id="feed-1", name="Aus dem Feed")]

    monkeypatch.setattr(products, "get_product_source", lambda: FakeFeed())
    assert [p["id"] for p in client.get("/api/products").json()] == ["feed-1"]


def test_broken_product_file_gives_500_with_message(client, monkeypatch, tmp_path):
    monkeypatch.setattr(products, "get_product_source",
                        lambda: JsonProductSource(tmp_path / "fehlt.json"))
    response = client.get("/api/products")
    assert response.status_code == 500
    assert "nicht gefunden" in response.json()["detail"]


def test_own_image_paths_are_allowed_but_not_other_sites():
    assert make_product(image_url="/img/products/prod-001.png").image_url.startswith("/img/")
    with pytest.raises(ValueError):
        make_product(image_url="//andere-seite.com/bild.png")   # sieht eigen aus, ist fremd
    with pytest.raises(ValueError):
        make_product(affiliate_url="/img/products/prod-001.png")  # Shop-Links bleiben https


def test_every_example_image_exists():
    from backend.config import FRONTEND_DIR
    for product in JsonProductSource().load():
        assert (FRONTEND_DIR / product.image_url.lstrip("/")).is_file(), product.id


def test_example_images_are_served(client):
    response = client.get("/img/products/prod-001.png")
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
