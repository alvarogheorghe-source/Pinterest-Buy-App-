"""Tests für echte Produkte von eBay (backend/ebay.py) – eBay wird simuliert.

Starten mit:  pytest -v
"""

from urllib.parse import parse_qs

import httpx
import pytest

from backend import ebay, products, storage


def item(item_id, title, price="24.99", condition="Gebraucht", affiliate=False, currency="EUR"):
    """Ein Suchergebnis so, wie die eBay Browse API es liefert."""
    data = {
        "itemId": item_id,
        "title": title,
        "price": {"value": price, "currency": currency},
        "condition": condition,
        "image": {"imageUrl": f"https://i.ebayimg.com/images/{item_id}.jpg"},
        "itemWebUrl": f"https://www.ebay.de/itm/{item_id}",
    }
    if affiliate:
        data["itemAffiliateWebUrl"] = f"https://www.ebay.de/itm/{item_id}?campid=123"
    return data


class FakeEbay:
    """Spielt die eBay-API. Merkt sich die Anfragen."""

    def __init__(self):
        self.requests = []
        self.token_ok = True
        self.results = {}  # Suchtext -> Liste von Ergebnissen

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/identity/v1/oauth2/token":
            if not self.token_ok:
                return httpx.Response(401, json={"error": "invalid_client"})
            return httpx.Response(200, json={"access_token": "ebay-token", "expires_in": 7200})
        if request.url.path == "/buy/browse/v1/item_summary/search":
            assert request.headers["Authorization"] == "Bearer ebay-token"
            query = request.url.params["q"]
            return httpx.Response(200, json={"itemSummaries": self.results.get(query, [])})
        return httpx.Response(404)

    def searches(self):
        return [r.url.params["q"] for r in self.requests if r.url.path.endswith("/search")]


@pytest.fixture
def fake_ebay(fake, monkeypatch):
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    monkeypatch.setenv("EBAY_CLIENT_ID", "id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    monkeypatch.delenv("EBAY_EPN_CAMPAIGN_ID", raising=False)
    ebay._token.clear()
    fake_api = FakeEbay()
    transport = httpx.MockTransport(fake_api.handler)
    monkeypatch.setattr(ebay, "_http", lambda: httpx.Client(transport=transport))
    return fake_api


def save_pins(*titles):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"],
                       "pins": [{"id": str(i), "title": t} for i, t in enumerate(titles)]})


# --- Suchbegriffe -----------------------------------------------------------------------------

def test_queries_follow_the_style_profile():
    pins = [{"title": "beige oversized hoodie"}, {"title": "beige hoodie"},
            {"title": "black cargo pants"}]
    queries = ebay.build_queries(pins, "mode")
    assert queries[0] == ("beige oversized Pullover", "Oberteile")   # meistgepinnt zuerst
    # Farbe/Stil aus den Hosen-Pins, nicht vom Hoodie übernommen; "utility" -> "Cargo"
    assert queries[1] == ("schwarz Cargo Hose", "Hosen")
    assert queries[2] == ("schwarz oversized Pullover", "Oberteile")  # zweitliebste Farbe
    assert len(queries) == ebay.QUERIES_PER_DEPARTMENT
    assert len({q for q, _ in queries}) == len(queries)                # keine doppelte Suche


def test_queries_without_pins_use_defaults():
    queries = ebay.build_queries([], "wohnen")
    assert [q for q, _ in queries] == ["Vase", "Lampe", "Kissen", "Beistelltisch"]


def test_style_words_ebay_sellers_use():
    queries = ebay.build_queries([{"title": "cozy goth vase"}], "wohnen")
    assert queries[0] == ("Gothic Vase", "Deko")


# --- eBay-Ergebnis -> Produkt -------------------------------------------------------------------

def test_item_becomes_product():
    product = ebay.to_product(item("v1|123|0", "Schwarze Oversized Bomberjacke Streetwear Gr. M"),
                              "mode", "Oberteile")
    assert product.id == "ebay-v1-123-0"                 # nur sichere Zeichen
    assert product.shop == "eBay · Second Hand"
    assert product.price == 24.99
    assert product.category == "Jacken"                   # aus dem Titel, nicht aus der Suche
    assert product.colors == ["schwarz"]
    assert product.style_tags == ["oversized", "streetwear"]
    assert product.sponsored is False                     # kein Partnerlink -> keine Werbung


def test_affiliate_link_makes_it_sponsored():
    product = ebay.to_product(item("2", "Hoodie neu", condition="Neu", affiliate=True), "mode", "Oberteile")
    assert product.affiliate_url.endswith("campid=123")
    assert product.sponsored is True and product.shop == "eBay"


def test_bigger_images_for_image_recognition():
    product = ebay.to_product(item("4", "Vase"), "wohnen", "Deko")
    assert product.image_url == "https://i.ebayimg.com/images/4.jpg"            # unverändert
    assert ebay.large_image("https://i.ebayimg.com/images/g/abc/s-l225.jpg") == \
        "https://i.ebayimg.com/images/g/abc/s-l500.jpg"


@pytest.mark.parametrize("title", [
    "Baby Strampler beige", "Kinder Hoodie Gr. 128", "Barbie Kleid", "Hundepullover",
    "Konvolut 10 Teile Damen Pullover", "Lampe defekt für Bastler", "Schnittmuster Kleid",
])
def test_junk_is_filtered(title):
    assert ebay.to_product(item("5", title), "mode", "Oberteile") is None


def test_houndstooth_is_not_junk():
    assert ebay.to_product(item("6", "Blazer Hundezahn Muster"), "mode", "Jacken") is not None


def test_unusable_items_are_skipped():
    assert ebay.to_product({"itemId": "x", "title": "ohne Preis"}, "mode", "Hosen") is None
    assert ebay.to_product(item("3", "Jacke", currency="GBP"), "mode", "Jacken") is None


# --- Quelle, Zwischenspeicher, API ----------------------------------------------------------------

def test_source_selection(fake, monkeypatch):
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
    assert products.source_name() == "demo"                       # keine Schlüssel
    monkeypatch.setenv("EBAY_CLIENT_ID", "id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    assert products.source_name() == "ebay"
    monkeypatch.setenv("PRODUCT_SOURCE", "demo")                  # erzwungen
    assert products.source_name() == "demo"


def test_ebay_products_in_the_shop_and_cache(fake_ebay, client):
    save_pins("beige oversized hoodie", "beige hoodie")
    fake_ebay.results["beige oversized Pullover"] = [
        item("10", "Beige Oversized Hoodie Damen", price="19.90"),
        item("11", "Schwarzer Pullover Rollkragen", price="12.00"),
    ]
    data = client.get("/api/recommendations?department=mode").json()
    assert data["source"] == "ebay"
    assert data["products"][0]["name"] == "Beige Oversized Hoodie Damen"   # passt am besten
    assert data["products"][0]["affiliate_url"] == "https://www.ebay.de/itm/10"
    searches = len(fake_ebay.searches())
    assert searches == 2 * ebay.QUERIES_PER_DEPARTMENT

    # Zweites Laden: aus dem Zwischenspeicher, keine neue Suche
    client.get("/api/recommendations?department=mode")
    client.get("/api/products/ebay-10")
    assert len(fake_ebay.searches()) == searches

    # Neue Pins -> Zwischenspeicher weg -> neue Suche
    save_pins("schwarze lederjacke")
    client.get("/api/recommendations?department=mode")
    assert len(fake_ebay.searches()) == 2 * searches


def test_wrong_keys_give_a_clear_message(fake_ebay, client):
    fake_ebay.token_ok = False
    response = client.get("/api/recommendations")
    assert response.status_code == 500
    assert "EBAY_CLIENT_ID" in response.json()["detail"]


def test_marketplace_and_affiliate_headers(fake_ebay, monkeypatch):
    monkeypatch.setenv("EBAY_MARKETPLACE", "EBAY_AT")
    monkeypatch.setenv("EBAY_EPN_CAMPAIGN_ID", "5338")
    ebay.search("Vase")
    request = fake_ebay.requests[-1]
    assert request.headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_AT"
    assert request.headers["X-EBAY-C-ENDUSERCTX"] == "affiliateCampaignId=5338"
    assert parse_qs(request.url.query.decode())["filter"] == [
        "buyingOptions:{FIXED_PRICE},price:[5..],priceCurrency:EUR"]
