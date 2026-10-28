"""Amazon-Partnerprogramm ohne Produkt-API (backend/amazon.py)."""

import pytest

from backend import amazon, region


@pytest.fixture
def tagged(monkeypatch):
    monkeypatch.setenv("AMAZON_PARTNER_TAG", "malipin-21")
    monkeypatch.setattr(region, "current", lambda: region.REGIONS["AT"])


def test_amazon_de_links_get_our_tag(tagged):
    item = amazon.apply({"affiliate_url": "https://www.amazon.de/dp/B0ABC?th=1", "sponsored": False})
    assert item["affiliate_url"] == "https://www.amazon.de/dp/B0ABC?th=1&tag=malipin-21"
    assert item["sponsored"] is True                         # jetzt Partnerlink -> "Werbung"


def test_other_peoples_tag_and_other_shops_stay(tagged):
    theirs = "https://www.amazon.de/dp/B0ABC?tag=someone-21"
    assert amazon.tag(theirs) == theirs
    assert amazon.tag("https://www.zalando.at/x") == "https://www.zalando.at/x"


def test_search_link_only_in_dach(tagged, monkeypatch):
    url = amazon.search_url(["schwarz", "Jeans", "", "damen", "schwarz"])
    assert url == "https://www.amazon.de/s?k=schwarz+Jeans+damen&tag=malipin-21"
    monkeypatch.setattr(region, "current", lambda: region.REGIONS["US"])
    assert amazon.search_url(["Jeans"]) is None


def test_without_tag_nothing_changes(monkeypatch):
    monkeypatch.delenv("AMAZON_PARTNER_TAG", raising=False)
    item = {"affiliate_url": "https://www.amazon.de/dp/B0ABC", "sponsored": False}
    assert amazon.apply(dict(item)) == item and amazon.search_url(["Jeans"]) is None


def test_product_page_offers_amazon_search(fake, client, monkeypatch):
    monkeypatch.setenv("AMAZON_PARTNER_TAG", "malipin-21")
    monkeypatch.setenv("PRODUCT_SOURCE", "demo")
    url = client.get("/api/products/prod-001", cookies={"country": "AT"}).json()["amazon_url"]
    assert url.startswith("https://www.amazon.de/s?k=") and url.endswith("&tag=malipin-21")
