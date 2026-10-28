"""Awin automatisch (feeds.discover_awin): angenommene Shops kommen von selbst dazu."""

import gzip
import json

import httpx
import pytest

from backend import feeds, storage
from tests.test_feeds import AWIN_CSV

LIST_CSV = (
    "Advertiser ID,Advertiser Name,Primary Region,Membership Status,Feed ID,Feed Name,Language,"
    "Vertical,Last Imported,Last Checked,No of products,URL\n"
    "11,Denim Store,DE,active,501,Denim DE,de,Fashion,2026-10-26,2026-10-26,5,"
    "https://productdata.awin.com/datafeed/download/apikey/geheim-123/fid/501/format/csv/\n"
    "12,Noch Nicht Store,AT,notjoined,502,Feed,de,Fashion,,,0,"
    "https://productdata.awin.com/datafeed/download/apikey/geheim-123/fid/502/\n"
    "13,UK Shop,GB,Active,503,UK,en,Home,,,0,https://productdata.awin.com/datafeed/download/apikey/geheim-123/fid/503/\n"
)
UK_CSV = AWIN_CSV.replace(",EUR,", ",GBP,")


@pytest.fixture
def awin_list(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(feeds, "CONFIG_FILE", tmp_path / "keine-feeds.json")
    monkeypatch.setenv("AWIN_FEED_KEY", "geheim-123")
    monkeypatch.delenv("AWIN_AUTO_FEEDS", raising=False)
    feeds._memory.update(mtime=None, products=[])
    state = {"list_down": False}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/datafeed/list/" in path:
            return httpx.Response(500) if state["list_down"] else httpx.Response(200, content=LIST_CSV.encode())
        if "/fid/501/" in path:
            return httpx.Response(200, content=gzip.compress(AWIN_CSV.encode()))
        if "/fid/503/" in path:
            return httpx.Response(200, content=UK_CSV.encode())
        return httpx.Response(404)

    monkeypatch.setattr(feeds, "_http", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    return state


def test_only_joined_shops_become_feeds(awin_list):
    found = feeds.discover_awin()
    assert [(f["name"], f["label"], f["countries"]) for f in found] == [
        ("awin-501", "Denim Store", ["DE", "AT", "CH"]), ("awin-503", "UK Shop", ["GB", "IE"])]
    assert feeds.configured()


def test_auto_feeds_are_imported_any_currency_and_key_never_stored(awin_list):
    result = feeds.import_all()
    assert result["feeds"]["awin-501"]["kept"] == 3          # auch die Dollar-Zeile (wird umgerechnet)
    uk = result["feeds"]["awin-503"]["products"]
    assert uk and uk[0]["currency"] == "GBP" and uk[0]["countries"] == ["GB", "IE"]
    assert "geheim-123" not in (storage.DATA_DIR / feeds.STORE_FILE).read_text()
    assert {f["name"] for f in feeds.known_feeds()} == {"awin-501", "awin-503"}


def test_list_down_keeps_the_old_products(awin_list):
    feeds.import_all()
    awin_list["list_down"] = True
    result = feeds.import_all()
    assert len(result["feeds"]["awin-501"]["products"]) == 3 and result["feeds"]["awin-501"]["error"]


def test_can_be_switched_off(awin_list, monkeypatch):
    monkeypatch.setenv("AWIN_AUTO_FEEDS", "0")
    assert feeds.discover_awin() == []
    json.dumps(feeds.known_feeds())


CANDIDATES_CSV = LIST_CSV + (
    "14,Westwing,DE,notjoined,504,Westwing DE,de,Home & Garden,,,12000,https://x/fid/504/\n"
    "14,Westwing,AT,notjoined,505,Westwing AT,de,Home & Garden,,,3000,https://x/fid/505/\n"
    "15,Kleiner Laden,DE,notjoined,506,Feed,de,Fashion,,,90000,https://x/fid/506/\n"
    "16,Bank Kredit,DE,notjoined,507,Feed,de,Finance,,,500,https://x/fid/507/\n"
    "17,ASOS,GB,pending,508,Feed,en,Fashion,,,40000,https://x/fid/508/\n"
)


def test_candidates_famous_first_without_joined_or_irrelevant(awin_list, monkeypatch, capsys):
    monkeypatch.setattr(feeds, "download", lambda url: CANDIDATES_CSV.encode())
    found = feeds.awin_candidates()
    assert [s["name"] for s in found] == ["ASOS", "Westwing", "Kleiner Laden", "Noch Nicht Store"]
    assert found[1]["products"] == 15000 and found[1]["regions"] == ["AT", "DE"]
    assert found[0]["pending"] and not found[2]["famous"]
    assert "Bank Kredit" in [s["name"] for s in feeds.awin_candidates(everything=True)]

    feeds.print_candidates()
    out = capsys.readouterr().out
    assert "★ Westwing" in out and "15.000 Produkte" in out
    assert "ASOS" not in out.split("★ = bekannte Marke")[1]      # schon beworben
    assert "geheim-123" not in out


def test_shops_from_other_countries_are_shown_where_they_deliver():
    assert feeds.awin_countries("PL", "AliExpress PL") == []            # weltweit
    assert feeds.awin_countries("NL", "Direct-Running NL") == ["NL"]     # Lieferung unbekannt
    assert feeds.awin_countries("PL", "Converse PL") == ["PL"]
    assert feeds.awin_countries("DE", "Unipolar DE") == ["DE", "AT", "CH"]
    assert feeds.awin_countries("US", "Shop") == ["US", "CA"]
    assert feeds.awin_countries("BR", "Loja") == ["BR"]


def test_list_shows_status_of_every_shop(awin_list, capsys):
    feeds.print_awin_list()
    out = capsys.readouterr().out
    assert "Denim Store" in out and "✓ wird geladen" in out
    assert "Noch Nicht Store" in out and "nicht angenommen" in out
    assert "geheim-123" not in out


def test_feed_without_currency_column_uses_the_shops_country(monkeypatch):
    feed = {"name": "awin-9", "preset": "awin", "currencies": [], "default_currency": "PLN"}
    row = {"aw_product_id": "1", "product_name": "Converse Hoodie", "aw_deep_link": "https://a/1",
           "merchant_image_url": "https://img/1.jpg", "search_price": "889", "merchant_name": "Converse PL",
           "merchant_category": "Bluzy"}
    product = feeds.to_product(row, feed)
    assert product and product.currency == "PLN"            # 889 Złoty, nicht 889 €


def test_verified_eu_shipping_shops(monkeypatch):
    monkeypatch.setattr(feeds, "SHIPS_EU", ["direct-running"])
    assert "AT" in feeds.awin_countries("NL", "Direct-Running NL")
