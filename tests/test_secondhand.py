"""Second Hand bei Vinted/willhaben/Depop suchen (backend/secondhand.py) – nur Such-Links."""

import pytest

from backend import region, secondhand


@pytest.fixture
def country():
    tokens = []
    yield lambda code: tokens.append(region._current.set(code))
    for token in reversed(tokens):
        region._current.reset(token)


def test_austria_gets_vinted_willhaben_and_depop(country):
    country("AT")
    links = secondhand.links(["Schwarz", "Hosen", "herren", ""])
    assert [link["name"] for link in links] == ["Vinted", "willhaben", "Depop"]
    assert links[0]["url"] == "https://www.vinted.at/catalog?search_text=schwarz+hosen+herren"
    assert "willhaben.at" in links[1]["url"] and "keyword=schwarz+hosen+herren" in links[1]["url"]


def test_germany_vinted_and_depop_elsewhere_only_depop(country):
    country("DE")
    assert [link["name"] for link in secondhand.links(["Jeans"])] == ["Vinted", "Depop"]
    country("US")
    assert [link["name"] for link in secondhand.links(["Jeans"])] == ["Depop"]


def test_depop_searches_in_english(country):
    """Depop ist englischsprachig: deutsche Begriffe werden übersetzt."""
    country("AT")
    depop = [link for link in secondhand.links(["schwarz", "Hosen", "herren"]) if link["name"] == "Depop"][0]
    assert depop["url"] == "https://www.depop.com/search/?q=black+pants+men"


def test_no_terms_no_links(country):
    country("AT")
    assert secondhand.links(["", None]) == []


def test_product_page_and_style_page_show_them(fake, client):
    data = client.get("/api/products/prod-006", cookies={"country": "AT"}).json()
    assert [link["name"] for link in data["secondhand"]] == ["Vinted", "willhaben", "Depop"]
    page = client.get("/stil/streetwear-icon", cookies={"country": "AT"}).text
    assert "vinted.at/catalog?search_text=" in page and "willhaben.at" in page
    assert "depop.com/search" in page
    us_page = client.get("/stil/streetwear-icon", cookies={"country": "US"}).text
    assert "vinted" not in us_page and "depop.com/search" in us_page
