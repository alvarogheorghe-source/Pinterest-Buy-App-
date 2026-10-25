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

def test_example_file_has_30_valid_products():
    items = JsonProductSource().load()  # wirft einen Fehler, falls ein Produkt ungültig ist
    assert len(items) == 30
    assert len({p.id for p in items}) == 30  # alle IDs eindeutig


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


def test_api_categories(client):
    assert client.get("/api/categories").json() == [
        "Accessoires", "Hosen", "Jacken", "Kleider & Röcke", "Oberteile", "Schuhe"]


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
