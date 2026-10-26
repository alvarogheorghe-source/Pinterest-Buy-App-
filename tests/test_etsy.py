"""Tests für echte Produkte von Etsy (backend/etsy.py) und das Mischen mit eBay.
Etsy und eBay werden simuliert – es geht nichts ins Internet.

Starten mit:  pytest -v
"""

import httpx
import pytest

from backend import ebay, etsy, storage
from backend.search_queries import ENGLISH, build_queries
from tests.test_ebay import FakeEbay, item


def listing(listing_id, title, amount=2499, currency="EUR", **extra):
    """Ein Angebot so, wie die Etsy Open API v3 es liefert (Preis in Cent + divisor)."""
    return {
        "listing_id": listing_id,
        "title": title,
        "url": f"https://www.etsy.com/listing/{listing_id}/x",
        "price": {"amount": amount, "divisor": 100, "currency_code": currency},
        "images": [{"url_570xN": f"https://i.etsystatic.com/{listing_id}.jpg"}],
        "shop": {"shop_name": "LinenLove"},
        "listing_type": "physical",
        "when_made": "made_to_order",
        **extra,
    }


class FakeEtsy:
    """Spielt die Etsy-API: Suche liefert nur IDs, /listings/batch die Details."""

    def __init__(self):
        self.requests = []
        self.key_ok = True
        self.results = {}  # Suchtext -> Liste von Angeboten

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.key_ok:
            return httpx.Response(403, json={"error": "Invalid API key"})
        path = request.url.path
        if path == "/v3/application/listings/active":
            found = self.results.get(request.url.params["keywords"], [])
            return httpx.Response(200, json={"count": len(found), "results": [
                {"listing_id": x["listing_id"]} for x in found]})
        if path == "/v3/application/listings/batch":
            ids = request.url.params["listing_ids"].split(",")
            assert request.url.params["includes"] == "Images,Shop"
            everything = [x for found in self.results.values() for x in found]
            return httpx.Response(200, json={"results": [
                x for x in everything if str(x["listing_id"]) in ids]})
        return httpx.Response(404)


@pytest.fixture
def fake_etsy(fake, monkeypatch):
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    monkeypatch.setenv("ETSY_API_KEY", "keystring")
    monkeypatch.setenv("ETSY_SHARED_SECRET", "secret")
    monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
    fake_api = FakeEtsy()
    transport = httpx.MockTransport(fake_api.handler)
    monkeypatch.setattr(etsy, "_http", lambda: httpx.Client(transport=transport))
    return fake_api


# --- Suchbegriffe auf Englisch --------------------------------------------------------------

def test_english_queries():
    pins = [{"title": "beige oversized hoodie"}, {"title": "schwarze cargo hose"}]
    queries = [q for q, _ in build_queries(pins, "mode", ENGLISH)]
    assert "beige oversized sweater" in queries
    assert "black cargo pants" in queries


# --- Etsy-Angebot -> Produkt ------------------------------------------------------------------

def test_listing_becomes_product():
    product = etsy.to_product(listing(42, "Beige Linen Pillow Cover &amp; Boho Style"),
                              "wohnen", "Textilien")
    assert product.id == "etsy-42"
    assert product.name == "Beige Linen Pillow Cover & Boho Style"   # HTML-Zeichen umgewandelt
    assert product.price == 24.99                                     # 2499 / 100
    assert product.shop == "Etsy · LinenLove"
    assert product.colors == ["beige"]
    assert "boho" in product.style_tags
    assert product.sponsored is False


def test_vintage_items():
    product = etsy.to_product(listing(7, "Denim jacket", when_made="1990s"), "mode", "Jacken")
    assert product.shop == "Etsy · Vintage"
    assert "vintage" in product.style_tags


@pytest.mark.parametrize("extra", [
    {"title": "Linen dress sewing pattern PDF"},       # digitale Datei
    {"title": "Printable wall art"},
    {"listing_type": "download"},
    {"is_supply": True},                                 # Bastelmaterial
    {"price": {"amount": 3000, "divisor": 100, "currency_code": "XYZ"}},   # unbekannte Währung
    {"price": {"amount": 299, "divisor": 100, "currency_code": "EUR"}},   # unter 5 €
    {"title": "Dog sweater beige"},
])
def test_unsuitable_listings_are_skipped(extra):
    data = {**listing(1, "Beige linen dress"), **extra}
    assert etsy.to_product(data, "mode", "Kleider & Röcke") is None


def test_key_and_secret_header(fake_etsy):
    etsy.search("vase")
    assert fake_etsy.requests[0].headers["x-api-key"] == "keystring:secret"


# --- Im Shop: allein und gemischt mit eBay ----------------------------------------------------

def save_pins(*titles):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"],
                       "pins": [{"id": str(i), "title": t} for i, t in enumerate(titles)]})


def test_etsy_products_in_the_shop(fake_etsy, client):
    save_pins("beige linen pillow", "boho vase")
    fake_etsy.results["beige natural pillow cover"] = [listing(5, "Beige Linen Pillow Cover")]
    data = client.get("/api/recommendations?department=wohnen").json()
    assert data["sources"] == ["etsy"]
    assert data["products"][0]["id"] == "etsy-5"


@pytest.fixture
def both(fake_etsy, monkeypatch):
    """eBay UND Etsy sind eingerichtet."""
    monkeypatch.setenv("EBAY_CLIENT_ID", "id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    ebay._token.clear()
    fake_ebay = FakeEbay()
    transport = httpx.MockTransport(fake_ebay.handler)
    monkeypatch.setattr(ebay, "_http", lambda: httpx.Client(transport=transport))
    return fake_ebay, fake_etsy


def test_ebay_and_etsy_are_mixed(both, client):
    fake_ebay, fake_etsy = both
    save_pins("beige oversized hoodie")
    fake_ebay.results["beige oversized Pullover"] = [item("1", "Beige Oversized Pullover")]
    fake_etsy.results["beige oversized sweater"] = [listing(2, "Beige oversized sweater")]
    data = client.get("/api/recommendations?department=mode").json()
    assert data["sources"] == ["ebay", "etsy"]
    assert {p["id"] for p in data["products"][:2]} == {"ebay-1", "etsy-2"}


def test_one_source_down_the_other_still_shows(both, client):
    fake_ebay, fake_etsy = both
    fake_etsy.key_ok = False
    save_pins("beige oversized hoodie")
    fake_ebay.results["beige oversized Pullover"] = [item("1", "Beige Oversized Pullover")]
    response = client.get("/api/recommendations?department=mode")
    assert response.status_code == 200
    assert [p["id"] for p in response.json()["products"]] == ["ebay-1"]


def test_all_sources_down_gives_a_clear_message(both, client):
    fake_ebay, fake_etsy = both
    fake_ebay.token_ok = False
    fake_etsy.key_ok = False
    response = client.get("/api/recommendations")
    assert response.status_code == 500
    assert "EBAY_CLIENT_ID" in response.json()["detail"]


def test_attribution_notice_on_pages(client):
    """Etsy verlangt den Hinweis – er steht auf jeder Seite mit Produkten bereit."""
    for page in ("/shop.html", "/produkt.html", "/merkliste.html"):
        assert etsy.ATTRIBUTION in " ".join(client.get(page).text.split())


def test_other_currencies_are_kept_and_converted_later():
    """Dollar-Preise bleiben Dollar – umgerechnet wird erst für die Person (currency.py)."""
    product = etsy.to_product({**listing(1, "Beige linen dress"),
                               "price": {"amount": 3000, "divisor": 100, "currency_code": "USD"}},
                              "mode", "Kleider & Röcke")
    assert (product.price, product.currency) == (30.0, "USD")
