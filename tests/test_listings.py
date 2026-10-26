"""Mehr Angebote & Sale-Preise: gemeinsamer Such-Speicher, Originalpreise, umgerechnet."""

from fastapi.testclient import TestClient

from backend import ebay, feeds, products, region, search_cache
from backend.main import app
from tests.test_ebay import fake_ebay, item, save_pins  # noqa: F401  (Fixture)
from tests.test_feeds import fake_feeds  # noqa: F401  (Fixture)


def sale_item(item_id, title, price, before):
    return {**item(item_id, title, price=price),
            "marketingPrice": {"originalPrice": {"value": before, "currency": "EUR"},
                               "discountPercentage": "30"}}


def test_same_search_is_shared_by_everyone(fake_ebay):
    """Zwei Personen, gleiche Suche -> eBay wird nur einmal gefragt."""
    fake_ebay.results["Baggy Jeans"] = [item("1", "Baggy Jeans blau")]
    assert ebay.search("Baggy Jeans") == ebay.search("Baggy Jeans")
    assert fake_ebay.searches().count("Baggy Jeans") == 1
    token = region.use("US")                               # anderer Marktplatz -> eigene Suche
    ebay.search("Baggy Jeans")
    region._current.reset(token)
    assert fake_ebay.searches().count("Baggy Jeans") == 2


def test_cache_keeps_only_needed_fields_and_cleans_up(fake, monkeypatch):
    monkeypatch.setattr(search_cache, "MAX_ENTRIES", 3)
    for i in range(5):
        search_cache.put(f"k{i}", [{"itemId": str(i)}])
    assert search_cache.get("k0") is None and search_cache.get("k4") == [{"itemId": "4"}]
    assert search_cache.get("k4", max_age=-1) is None                  # zu alt


def test_sale_price_only_when_really_reduced():
    assert products.sale_price(70, "100") == 100.0
    assert products.sale_price(99, 100) is None                         # 1 % ist kein Sale
    assert products.sale_price(50, None) is None and products.sale_price(50, "abc") is None


def test_ebay_sale_price_reaches_the_shop_converted(fake_ebay):
    save_pins("beige oversized hoodie")
    fake_ebay.results["beige oversized Hoodie"] = [sale_item("7", "Beige Oversized Hoodie", "35.00", "50.00")]
    product = next(p for p in ebay.EbayProductSource().load() if p.id == "ebay-7")
    assert product.original_price == 50.0
    austria = TestClient(app, cookies={"country": "AT"})
    shown = next(p for p in austria.get("/api/recommendations?department=mode").json()["products"]
                 if p["id"] == "ebay-7")
    assert shown["local_original_price"] == 50.0 and shown["local_price"] == 35.0


def test_feed_rrp_becomes_original_price():
    row = {"aw_product_id": "9", "product_name": "Wide Leg Jeans", "aw_deep_link": "https://a.example/9",
           "merchant_image_url": "https://i.example/9.jpg", "search_price": "39.90", "currency": "EUR",
           "rrp_price": "59.90", "merchant_category": "Jeans"}
    product = feeds.to_product(row, {"name": "awin", "preset": "awin"})
    assert (product.price, product.original_price) == (39.9, 59.9)
