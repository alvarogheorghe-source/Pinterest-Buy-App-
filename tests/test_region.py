"""Land & Währung (backend/region.py, backend/currency.py) – weltweit nutzbar."""

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import currency, ebay, feeds, products, region
from backend.main import app
from tests.test_ebay import fake_ebay, item, save_pins  # noqa: F401  (Fixture)
from tests.test_feeds import fake_feeds  # noqa: F401  (Fixture)

ECB_XML = b"""<?xml version="1.0"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
  xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube><Cube time="2026-10-26">
  <Cube currency="USD" rate="1.10"/><Cube currency="GBP" rate="0.80"/><Cube currency="CHF" rate="0.94"/>
  <Cube currency="CAD" rate="1.50"/><Cube currency="AUD" rate="1.70"/></Cube></Cube></gesmes:Envelope>"""


@pytest.mark.parametrize("cookie,geo,accept,expected", [
    ("country=GB", "", "de-AT", "GB"),                 # bewusste Wahl gewinnt
    ("", "CA", "en-US", "CA"),                          # Hosting-Ländercode
    ("", "", "en-US,en;q=0.9", "US"),
    ("", "", "de-CH,de;q=0.9", "CH"),
    ("", "", "en", "US"),
    ("", "", "fr-FR", "AT"),                            # unbekannt -> Standard
    ("country=XX", "", "", "AT"),
])
def test_choose_region(cookie, geo, accept, expected):
    assert region.choose(cookie, geo, accept) == expected


def test_convert_and_ecb_rates(fake, monkeypatch):
    table = {"EUR": 1.0, "USD": 1.1, "GBP": 0.8}
    assert currency.convert(20, "EUR", "USD", table) == 22.0
    assert currency.convert(22, "USD", "GBP", table) == 16.0
    assert currency.convert(5, "XYZ", "EUR", table) is None
    monkeypatch.setattr(currency, "_http", lambda: httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=ECB_XML))))
    assert currency.refresh()["GBP"] == 0.8
    assert currency.rates()["USD"] == 1.10                               # gespeichert


def test_prices_and_budget_in_the_persons_currency(fake):
    us = TestClient(app, cookies={"country": "US"})
    data = us.get("/api/recommendations?department=mode&max_price=25").json()
    assert data["currency"] == "USD" and data["products"]
    for product in data["products"]:
        assert product["local_currency"] == "USD" and product["converted"] is True
        assert product["local_price"] <= 25                              # Budget in Dollar
    assert data["products"][0]["currency"] == "EUR"                       # Original bleibt
    at = TestClient(app, cookies={"country": "AT"})
    first = at.get("/api/recommendations?department=mode").json()["products"][0]
    assert first["converted"] is False and first["local_price"] == first["price"]
    countries = us.get("/api/region").json()
    assert countries["country"] == "US" and {"AT", "US", "GB"} <= {c["code"] for c in countries["countries"]}


def test_ebay_uses_the_marketplace_of_the_country(fake_ebay):
    save_pins("beige oversized hoodie")
    fake_ebay.results["beige oversized Hoodie"] = [item("1", "Hoodie beige", currency="EUR")]
    fake_ebay.results["beige oversized hoodie"] = [item("2", "Beige hoodie", currency="USD")]
    ebay._token.clear()
    token = region.use("AT")
    assert [p.id for p in ebay.EbayProductSource().load()] == ["ebay-1"]
    region._current.reset(token)
    token = region.use("US")                                             # anderes Land -> neu suchen
    products = ebay.EbayProductSource().load()
    region._current.reset(token)
    assert [p.id for p in products] == ["ebay-2"] and products[0].currency == "USD"
    searches = [r for r in fake_ebay.requests if r.url.path.endswith("/search")]
    assert {r.headers["X-EBAY-C-MARKETPLACE-ID"] for r in searches} == {"EBAY_AT", "EBAY_US"}
    assert any("priceCurrency:USD" in r.url.params["filter"] for r in searches)


def test_feeds_only_show_products_delivered_to_the_country(fake_feeds):
    feeds.import_all()
    assert all(p.countries == [] for p in feeds.stored_products())       # Test-Feeds ohne Länder
    restricted = [p.model_copy(update={"countries": ["AT"]}) for p in feeds.stored_products()]
    assert products.filter_products(restricted, country="US") == []
    assert len(products.filter_products(restricted, country="AT")) == len(restricted)
