"""Skimlinks (backend/skimlinks.py): nur Links ohne Partnerprogramm, immer als Werbung."""

from urllib.parse import parse_qs, urlparse

from backend import skimlinks


def test_off_without_id(monkeypatch):
    monkeypatch.delenv("SKIMLINKS_ID", raising=False)
    item = {"affiliate_url": "https://www.etsy.com/listing/1", "sponsored": False}
    assert skimlinks.apply(dict(item)) == item


def test_wraps_plain_shop_links_and_marks_them_as_ads(monkeypatch):
    monkeypatch.setenv("SKIMLINKS_ID", "123X456")
    item = skimlinks.apply({"affiliate_url": "https://www.etsy.com/listing/1?a=b", "sponsored": False})
    url = urlparse(item["affiliate_url"])
    assert url.netloc == "go.skimresources.com" and item["sponsored"] is True
    assert parse_qs(url.query) == {"id": ["123X456"], "xs": ["1"], "url": ["https://www.etsy.com/listing/1?a=b"]}
    pin = skimlinks.apply({"link": "https://www.zara.com/at/de/hose-p1.html"})
    assert pin["link"].startswith("https://go.skimresources.com/") and pin["sponsored"]


def test_existing_affiliate_links_stay(monkeypatch):
    monkeypatch.setenv("SKIMLINKS_ID", "123X456")
    for url in ("https://www.awin1.com/pclick.php?p=1", "https://s.click.aliexpress.com/e/x",
                "https://www.ebay.at/itm/1?mkcid=1&campid=5338"):
        assert skimlinks.apply({"affiliate_url": url, "sponsored": False})["affiliate_url"] == url
    sponsored = {"affiliate_url": "https://shop.de/x", "sponsored": True}
    assert skimlinks.apply(dict(sponsored)) == sponsored
