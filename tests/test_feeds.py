"""Produkt-Feeds (backend/feeds.py) – Feeds werden simuliert, keine echten Downloads."""

import gzip
import json

import httpx
import pytest

from backend import feeds, products, shops, storage
from backend.shops import ShopInput

AWIN_CSV = (
    "aw_product_id,product_name,aw_deep_link,merchant_image_url,search_price,currency,"
    "merchant_name,merchant_category,colour,product_short_description\n"
    "1,Baggy Jeans Light Wash,https://www.awin1.com/pclick.php?p=1,https://img.shop/1.jpg,49.90,EUR,"
    "Denim Store,Damen > Hosen > Jeans,blau,Weite Baggy Jeans\n"
    "2,Keramikvase Sand,https://www.awin1.com/pclick.php?p=2,https://img.shop/2.jpg,24.99,EUR,"
    "Home Store,Wohnen > Deko,beige,Handgemacht\n"
    "3,Geschenkgutschein,https://www.awin1.com/pclick.php?p=3,https://img.shop/3.jpg,25.00,EUR,"
    "Denim Store,Gutscheine,,\n"                                              # weder Mode noch Wohnen
    "4,Bootcut Jeans,https://www.awin1.com/pclick.php?p=4,https://img.shop/4.jpg,59.00,USD,"
    "Denim Store,Jeans,,\n"                                                   # falsche Währung
    "5,Hoodie ohne Bild,https://www.awin1.com/pclick.php?p=5,,19.00,EUR,Denim Store,Hoodies,,\n"
)
GOOGLE_XML = b"""<?xml version="1.0"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0"><channel>
  <item><g:id>A1</g:id><g:title>Chelsea Boots Wildleder braun</g:title>
    <g:link>https://track.example/a1</g:link><g:image_link>https://img.example/a1.jpg</g:image_link>
    <g:price>89,95 EUR</g:price><g:brand>Boot Co</g:brand><g:product_type>Schuhe</g:product_type></item>
  <item><g:id>A2</g:id><g:title>Nike Replica Sneaker 1:1</g:title>
    <g:link>https://track.example/a2</g:link><g:image_link>https://img.example/a2.jpg</g:image_link>
    <g:price>39.00 EUR</g:price><g:product_type>Schuhe</g:product_type></item>
</channel></rss>"""

FEEDS = [
    {"name": "awin", "label": "Awin", "preset": "awin", "url": "https://feeds.example/awin?key={AWIN_FEED_KEY}"},
    {"name": "boots", "label": "Boots", "preset": "google", "url": "https://feeds.example/google",
     "counterfeit_filter": True},
]


@pytest.fixture
def fake_feeds(fake, monkeypatch, tmp_path):
    config = tmp_path / "feeds.json"
    config.write_text(json.dumps(FEEDS))
    monkeypatch.setattr(feeds, "CONFIG_FILE", config)
    monkeypatch.setenv("AWIN_FEED_KEY", "geheim")
    monkeypatch.setenv("AWIN_AUTO_FEEDS", "0")          # hier nur feeds.json (Auto: test_awin_feeds.py)
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    for name in ("EBAY_CLIENT_ID", "ETSY_API_KEY", "ALIEXPRESS_APP_KEY"):
        monkeypatch.delenv(name, raising=False)
    feeds._memory.update(mtime=None, products=[])
    state = {"down": False, "requests": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(str(request.url))
        if state["down"]:
            return httpx.Response(500)
        if request.url.path == "/awin":
            assert request.url.params["key"] == "geheim"
            return httpx.Response(200, content=gzip.compress(AWIN_CSV.encode()))
        return httpx.Response(200, content=GOOGLE_XML)

    monkeypatch.setattr(feeds, "_http", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    return state


def test_import_awin_and_google_feeds(fake_feeds):
    result = feeds.import_all()
    awin = {p["id"]: p for p in result["feeds"]["awin"]["products"]}
    assert set(awin) == {"awin-1", "awin-2"}             # Gutschein, USD, ohne Bild: raus
    jeans = awin["awin-1"]
    assert (jeans["category"], jeans["department"], jeans["price"]) == ("Hosen", "mode", 49.9)
    assert jeans["shop"] == "Denim Store" and jeans["sponsored"] is True
    assert awin["awin-2"]["department"] == "wohnen"
    boots = result["feeds"]["boots"]["products"]
    assert [p["name"] for p in boots] == ["Chelsea Boots Wildleder braun"]   # Fake gefiltert
    assert boots[0]["price"] == 89.95 and boots[0]["colors"] == ["braun"]


def test_feed_products_appear_in_the_shop(fake_feeds, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": str(i), "title": "baggy light wash jeans"} for i in range(3)]})
    data = client.get("/api/recommendations?department=mode").json()
    assert "feeds" in data["sources"]
    assert data["products"][0]["id"] == "awin-1"         # Baggy Light Wash passt am besten
    assert client.get("/api/products/awin-1").status_code == 200


def test_trusted_merchant_in_a_feed(fake_feeds):
    feeds.import_all()
    shops.add(ShopInput(platform="awin", seller="Denim Store", name="Denim Store"))
    marked = {p.id: p.trusted for p in shops.mark(feeds.stored_products())}
    assert marked["awin-1"] is True and marked["awin-2"] is False


def test_missing_key_and_broken_feed(fake_feeds, monkeypatch):
    feeds.import_all()
    fake_feeds["down"] = True
    result = feeds.import_all()                          # Feed fällt aus -> alte Produkte bleiben
    assert result["feeds"]["awin"]["error"] and len(result["feeds"]["awin"]["products"]) == 2
    monkeypatch.delenv("AWIN_FEED_KEY")
    with pytest.raises(feeds.FeedError, match="AWIN_FEED_KEY fehlt"):
        feeds.resolve_url(FEEDS[0]["url"])


def test_secret_key_never_stored(fake_feeds):
    feeds.import_all()
    assert "geheim" not in (storage.DATA_DIR / feeds.STORE_FILE).read_text()


@pytest.mark.parametrize("text,expected", [
    ("12,99 EUR", (12.99, "EUR")), ("EUR 12.99", (12.99, "EUR")), ("1.299,00", (1299.0, None)),
    ("1,299.00 USD", (1299.0, "USD")), ("19", (19.0, None)), ("", (None, None)),
])
def test_prices(text, expected):
    assert feeds.parse_price(text) == expected


def test_semicolon_csv_with_own_columns():
    rows = list(feeds.read_rows("Artikel;Titel;Preis;Link;Bild\n7;Strickpullover beige;29,90;"
                                "https://t.example/7;https://i.example/7.jpg\n".encode()))
    feed = {"name": "eigen", "preset": "generic", "fields": {
        "id": "Artikel", "name": "Titel", "price": "Preis", "url": "Link", "image": "Bild"}}
    product = feeds.to_product(rows[0], feed)
    assert (product.id, product.category, product.price) == ("eigen-7", "Oberteile", 29.9)


def test_bad_config_is_rejected(tmp_path):
    bad = tmp_path / "feeds.json"
    bad.write_text(json.dumps([{"name": "Mit Leerzeichen", "url": "https://x"}]))
    with pytest.raises(feeds.FeedError):
        feeds.load_config(bad)
    assert products.source_names()   # App läuft trotzdem
