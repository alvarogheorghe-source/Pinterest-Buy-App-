"""Second Hand bei Vinted/willhaben suchen (backend/secondhand.py) – nur Such-Links."""

import pytest

from backend import region, secondhand


@pytest.fixture
def country():
    tokens = []
    yield lambda code: tokens.append(region._current.set(code))
    for token in reversed(tokens):
        region._current.reset(token)


def test_austria_gets_vinted_and_willhaben(country):
    country("AT")
    links = secondhand.links(["Schwarz", "Hosen", "herren", ""])
    assert [link["name"] for link in links] == ["Vinted", "willhaben"]
    assert links[0]["url"] == "https://www.vinted.at/catalog?search_text=schwarz+hosen+herren"
    assert "willhaben.at" in links[1]["url"] and "keyword=schwarz+hosen+herren" in links[1]["url"]


def test_germany_only_vinted_and_elsewhere_nothing(country):
    country("DE")
    assert [link["name"] for link in secondhand.links(["Jeans"])] == ["Vinted"]
    country("US")
    assert secondhand.links(["Jeans"]) == []


def test_no_terms_no_links(country):
    country("AT")
    assert secondhand.links(["", None]) == []


def test_product_page_and_style_page_show_them(fake, client):
    data = client.get("/api/products/prod-006", cookies={"country": "AT"}).json()
    assert [link["name"] for link in data["secondhand"]] == ["Vinted", "willhaben"]
    page = client.get("/stil/streetwear-icon", cookies={"country": "AT"}).text
    assert "vinted.at/catalog?search_text=" in page and "willhaben.at" in page
    assert "vinted" not in client.get("/stil/streetwear-icon", cookies={"country": "US"}).text
