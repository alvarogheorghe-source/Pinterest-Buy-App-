"""Outfit-Seiten für Google/Pinterest (backend/outfit_pages.py)."""

import re

import pytest

from backend import outfit_pages, style_guide
from backend.products import Product


def product(pid, name, category, price, gender=None, tags=("streetwear",)):
    return Product(id=pid, name=name, shop="Testshop", price=price, category=category,
                   style_tags=list(tags), colors=["schwarz"], gender=gender,
                   image_url=f"https://img.example/{pid}.jpg",
                   affiliate_url=f"https://shop.example/{pid}")


@pytest.fixture
def catalog(monkeypatch):
    items = []
    monkeypatch.setattr(outfit_pages, "catalog", lambda: items)
    monkeypatch.setattr(outfit_pages, "_cache", {})
    return items


PAGE = outfit_pages.BY_SLUG["streetwear-outfit-herren-unter-100"]


def test_outfit_is_one_piece_per_slot_within_budget(catalog):
    catalog += [product("h1", "Oversized Hoodie", "Oberteile", 40, "herren"),
                product("h2", "Oversized Hoodie Premium", "Oberteile", 90, "herren"),
                product("c1", "Cargohose", "Hosen", 35, "herren"),
                product("s1", "Chunky Sneaker", "Schuhe", 20, "herren"),
                product("s2", "Chunky Sneaker Luxus", "Schuhe", 80, "herren")]
    look = outfit_pages.outfit(PAGE, outfit_pages.candidates(PAGE))
    assert [i["category"] for i in look] == ["Oberteile", "Hosen", "Schuhe"]
    assert sum(i["local_price"] for i in look) <= PAGE.budget
    assert {i["id"] for i in look} == {"h1", "c1", "s1"}


def test_mens_page_skips_womens_pieces(catalog):
    catalog += [product("w1", "Streetwear Hoodie", "Oberteile", 30, "damen"),
                product("b1", "Ballerinas Streetwear", "Schuhe", 20),       # ohne Angabe, aber klar Damen
                product("m1", "Streetwear Hoodie", "Oberteile", 30, "herren"),
                product("u1", "Streetwear Cargo", "Hosen", 30)]             # unisex ist okay
    ids = {i["id"] for i in outfit_pages.candidates(PAGE)}
    assert ids == {"m1", "u1"}


def test_one_piece_less_rather_than_no_outfit(catalog):
    catalog += [product("o1", "Streetwear Hoodie", "Oberteile", 60, "herren"),
                product("h1", "Streetwear Cargo", "Hosen", 30, "herren"),
                product("s1", "Streetwear Sneaker", "Schuhe", 50, "herren")]   # alle drei: 140 €
    look = outfit_pages.outfit(PAGE, outfit_pages.candidates(PAGE))
    assert len(look) == 2 and sum(i["local_price"] for i in look) <= PAGE.budget


def test_page_shows_the_live_catalog(fake, client, catalog):
    catalog += [product("o1", "Streetwear Hoodie", "Oberteile", 30, "herren"),
                product("h1", "Streetwear Cargo", "Hosen", 30, "herren")]
    html = client.get("/outfits/streetwear-outfit-herren-unter-100").text
    assert "<h1 class=\"outfit-title\">Streetwear Outfit Herren unter 100 €</h1>" in html
    assert 'href="/produkt.html?id=o1"' in html and "€ 60" in html             # Zusammen: € 60
    assert '<link rel="canonical" href="https://malipin.com/outfits/streetwear-outfit-herren-unter-100"' in html
    # Neuer Shop / neues Teil -> nach Ablauf des Zwischenspeichers ist es da
    catalog.append(product("s1", "Streetwear Sneaker", "Schuhe", 20, "herren"))
    outfit_pages._cache.clear()
    assert 'href="/produkt.html?id=s1"' in client.get("/outfits/streetwear-outfit-herren-unter-100").text


def test_every_page_renders_and_is_in_the_sitemap(fake, client, catalog):
    sitemap = client.get("/sitemap.xml").text
    index = client.get("/outfits").text
    vibes = {v["slug"].removeprefix("vibe-") for v in style_guide.guide("de")["vibes"]}
    for page in outfit_pages.PAGES:
        html = client.get(f"/outfits/{page.slug}").text
        assert f"<title>{page.title} | Malipin</title>" in html.replace("&amp;", "&")
        assert 80 <= len(page.description) <= 170, page.slug                  # passt in Google
        assert f"https://malipin.com/outfits/{page.slug}" in sitemap
        assert f'href="/outfits/{page.slug}"' in index
        assert set(page.related) <= vibes, page.slug
        assert set(page.slots) <= {"Oberteile", "Hosen", "Jacken", "Kleider & Röcke", "Schuhe",
                                   "Accessoires"}
    assert client.get("/outfits/gibtsnicht").status_code == 404
    assert len({p.slug for p in outfit_pages.PAGES}) == len(outfit_pages.PAGES)


def test_style_pages_link_to_matching_outfits(fake, client, catalog):
    html = client.get("/stil/streetwear-icon").text
    assert re.search(r'href="/outfits/streetwear-outfit-herren-unter-100"', html)
