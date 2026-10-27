"""Tests für echte Produkte von eBay (backend/ebay.py) – eBay wird simuliert.

Starten mit:  pytest -v
"""

from urllib.parse import parse_qs

import httpx
import pytest

from backend import ebay, products, storage
from backend.search_queries import QUERIES_PER_DEPARTMENT, build_queries


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
    monkeypatch.delenv("ETSY_API_KEY", raising=False)
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
    queries = build_queries(pins, "mode")
    assert queries[0] == ("beige oversized Hoodie", "Oberteile")   # meistgepinnt zuerst, genaues Teil
    # Farbe/Stil aus den Hosen-Pins, nicht vom Hoodie übernommen; "utility" -> "Cargo"
    assert queries[1] == ("schwarz Cargohose", "Hosen")
    assert queries[2] == ("schwarz oversized Hoodie", "Oberteile")  # zweitliebste Farbe
    assert len(queries) == QUERIES_PER_DEPARTMENT
    assert len({q for q, _ in queries}) == len(queries)                # keine doppelte Suche


def test_queries_without_pins_use_trends():
    """Neue Besucher ohne Pins: gefragte Teile statt eines leeren Shops."""
    queries = build_queries([], "wohnen")
    assert queries[:3] == [("Keramikvase", "Deko"), ("Pilz Lampe", "Leuchten"),
                           ("Boucle Kissen", "Textilien")]
    assert len(queries) == QUERIES_PER_DEPARTMENT


def test_second_hand_search_for_the_favourite_part():
    pins = [{"title": "light wash baggy jeans"}, {"title": "baggy jeans light wash"}]
    queries = build_queries(pins, "mode")
    vintage = next(q for q in queries if q[0].startswith("Vintage "))
    assert vintage[0] == "Vintage " + queries[0][0] and vintage.fallback == "Vintage Jeans"


def test_style_words_ebay_sellers_use():
    queries = build_queries([{"title": "cozy goth vase"}], "wohnen")
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
    monkeypatch.delenv("ETSY_API_KEY", raising=False)
    assert products.source_names() == ["demo"]                    # keine Schlüssel
    monkeypatch.setenv("EBAY_CLIENT_ID", "id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    assert products.source_names() == ["ebay"]
    monkeypatch.setenv("ETSY_API_KEY", "key")
    assert products.source_names() == ["ebay", "etsy"]
    assert isinstance(products.get_product_source().inner, products.CombinedSource)
    monkeypatch.setenv("PRODUCT_SOURCE", "demo")                  # erzwungen
    assert products.source_names() == ["demo"]


def test_ebay_products_in_the_shop_and_cache(fake_ebay, client):
    save_pins("beige oversized hoodie", "beige hoodie")
    fake_ebay.results["beige oversized Pullover"] = [
        item("10", "Beige Oversized Hoodie Damen", price="19.90"),
        item("11", "Schwarzer Pullover Rollkragen", price="12.00"),
    ]
    data = client.get("/api/recommendations?department=mode").json()
    assert data["sources"] == ["ebay"]
    assert data["products"][0]["name"] == "Beige Oversized Hoodie Damen"   # passt am besten
    assert data["products"][0]["affiliate_url"] == "https://www.ebay.de/itm/10"
    searches = len(fake_ebay.searches())
    # 4 Suchen pro Welt – plus breitere Suchen, wo die genaue zu wenig fand (Sicherheitsnetz)
    assert 2 * QUERIES_PER_DEPARTMENT <= searches <= 4 * QUERIES_PER_DEPARTMENT

    # Zweites Laden: aus dem Zwischenspeicher, keine neue Suche
    client.get("/api/recommendations?department=mode")
    client.get("/api/products/ebay-10")
    assert len(fake_ebay.searches()) == searches

    # Neue Pins -> Zwischenspeicher weg -> neue Suche
    save_pins("schwarze lederjacke")
    client.get("/api/recommendations?department=mode")
    assert len(fake_ebay.searches()) > searches


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


def test_sandbox_keys_and_ebay_reason(fake_ebay, client, monkeypatch):
    fake_ebay.token_ok = False
    assert "invalid_client" in client.get("/api/recommendations").json()["detail"]
    # Sandbox-Keys -> eBays Test-Server
    fake_ebay.token_ok = True
    ebay._token.clear()
    monkeypatch.setenv("EBAY_CLIENT_ID", "Malipin-app-SBX-1234")
    assert client.get("/api/recommendations").status_code == 200
    assert {r.url.host for r in fake_ebay.requests} >= {"api.sandbox.ebay.com"}


def test_check_command(fake_ebay, capsys):
    save_pins("beige oversized hoodie")
    fake_ebay.results["beige oversized Pullover"] = [item("10", "Beige Oversized Hoodie")]
    ebay.main()
    out = capsys.readouterr().out
    assert "Anmeldung: ok" in out and "Zusammen: 1 Angebote" in out


def test_failed_source_is_shown_not_silent(fake_ebay, client):
    """eBay fällt aus, Foto-Ergebnisse gibt es noch -> Shop zeigt Hinweis statt still 0 Angebote."""
    products.remember_photo_results([products.Product(
        id="ebay-alt", name="Alte Jacke", shop="eBay", price=20, department="mode",
        category="Jacken", image_url="https://i.ebayimg.com/a.jpg",
        affiliate_url="https://www.ebay.de/itm/a")])
    fake_ebay.token_ok = False
    data = client.get("/api/recommendations?department=mode").json()
    assert data["warnings"][0]["source"] == "ebay"
    assert "Anmeldung" in data["warnings"][0]["message"]


def test_support_report_never_contains_the_secret(fake_ebay, monkeypatch):
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "PRD-supersecret-123")
    fake_ebay.token_ok = False
    report = ebay.support_report()
    assert "invalid_client" in report and "HTTP 401" in report
    assert "supersecret" not in report and "PRD-supersecret" not in report
    assert "id" in report.split("App ID (Client ID):")[1].splitlines()[0]


def test_same_quality_rules_as_feeds():
    from backend.ebay import to_product
    assert to_product(item("1", "Herren Boxershorts 3er Pack"), "mode", "Hosen") is None
    assert to_product(item("2", "Kraftstoffschlauch Motor Ersatzteil", "15"), "mode", "Hosen") is None
    vintage = to_product(item("3", "Vintage Levis Jeans Herren", "9.50"), "mode", "Hosen")
    assert vintage and vintage.gender == "herren"                # gebraucht darf günstig sein
    assert to_product(item("4", "Damen Jeans Basic", "6.00", condition="Neu"), "mode", "Hosen") is None


def test_old_cached_results_are_dropped_when_rules_change(fake, monkeypatch):
    from backend import products, storage

    class Source(products.CachedSource):
        name, cache_file = "test", "test_cache.json"
        calls = 0

        def fetch(self):
            Source.calls += 1
            return []

    Source().load()
    Source().load()
    assert Source.calls == 1                                  # zwischengespeichert
    monkeypatch.setattr(products, "RULES_VERSION", products.RULES_VERSION + 1)
    Source().load()
    assert Source.calls == 2                                  # neue Regeln -> neu suchen
    assert storage.read_json("test_cache.json")["version"] == products.RULES_VERSION
