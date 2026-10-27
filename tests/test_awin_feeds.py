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
