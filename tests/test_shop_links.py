"""Tests für Teil A, Schritt 1: Shop-Links in Pins erkennen.

Starten mit:  pytest -v
"""

import pytest

from backend import storage
from backend.shop_links import detect_platform, find_pin_items


@pytest.mark.parametrize("url, platform, platform_type", [
    ("https://www.depop.com/products/seller-beige-hoodie/", "Depop", "Second Hand"),
    ("https://www.vinted.at/items/123-pullover", "Vinted", "Second Hand"),
    ("https://www.vinted.de/items/123-pullover", "Vinted", "Second Hand"),
    ("https://www.willhaben.at/iad/kaufen-und-verkaufen/d/jacke-123/", "willhaben", "Second Hand"),
    ("https://www.ebay.co.uk/itm/123", "eBay", "Second Hand"),
    ("https://www.etsy.com/listing/123/vintage-jacket", "Etsy", "Second Hand"),
    ("https://www.zalando.at/jacke-123.html", "Zalando", "Shop"),
    ("https://www2.hm.com/de_at/productpage.123.html", "H&M", "Shop"),
    ("https://depop.com/products/x/", "Depop", "Second Hand"),  # ohne www
])
def test_known_platforms(url, platform, platform_type):
    assert detect_platform(url) == {"platform": platform, "platform_type": platform_type}


def test_unknown_shop_recognized_by_product_path():
    assert detect_platform("https://www.kleiner-laden.at/products/beige-hoodie") == {
        "platform": "kleiner-laden.at", "platform_type": "Shop"}


@pytest.mark.parametrize("url", [
    None,
    "",
    "https://www.pinterest.com/pin/123/",            # Pinterest selbst
    "https://pin.it/abc",                             # Pinterest-Kurzlink
    "https://www.instagram.com/p/abc/",               # Instagram (trotz /p/)
    "https://modeblog.at/mein-herbst-outfit",         # Blog, kein Shop
    "https://depop.com.betrug.net/products/x",        # gefälschte Depop-Adresse
    "https://vinted.betrug.net/products/x",           # gefälschte Vinted-Adresse
    "https://notdepop.com/",                          # anderer Name, keine Produktseite
    "javascript:alert('hack')",                       # gefährlicher Link
    "ftp://depop.com/products/x",                     # kein Web-Link
])
def test_not_a_shop(url):
    assert detect_platform(url) is None


def test_find_pin_items_keeps_only_shop_pins():
    pins = [
        {"id": "1", "title": "Hoodie", "link": "https://www.depop.com/products/a/"},
        {"id": "2", "title": "Outfit-Idee", "link": "https://modeblog.at/outfit"},
        {"id": "3", "title": "Ohne Link"},
    ]
    items = find_pin_items(pins)
    assert [i["id"] for i in items] == ["1"]
    assert items[0]["platform"] == "Depop"
    assert items[0]["title"] == "Hoodie"  # Pin-Daten bleiben erhalten


def test_api_pin_items(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        {"id": "1", "title": "Cargo", "link": "https://www.vinted.at/items/1"},
        {"id": "2", "title": "Inspo", "link": None},
    ]})
    items = client.get("/api/pin-items").json()
    assert [(i["id"], i["platform"]) for i in items] == [("1", "Vinted")]


def test_old_pins_without_link_field_still_work(fake, client):
    """Pins, die vor diesem Update gespeichert wurden, haben noch kein "link"-Feld."""
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [{"id": "1", "title": "Alt"}]})
    assert client.get("/api/pin-items").json() == []
