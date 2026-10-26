"""Marken in Pins erkennen (backend/brands.py) und gezielt danach suchen."""

from backend.brands import BRANDS
from backend.matching import CATEGORY_SYNONYMS, build_style_profile
from backend.search_queries import ENGLISH, build_queries


def test_every_brand_has_a_known_category():
    for name, brand in BRANDS.items():
        assert brand.category in CATEGORY_SYNONYMS, name
        assert brand.words and brand.prompt, name


def test_brands_from_text_and_image():
    pins = [{"title": "Adidas Samba outfit"}, {"title": "my new sambas"},
            {"title": "", "image_brands": ["Adidas Samba"], "image_categories": ["Schuhe"]},
            {"title": "samba dance class"}]                       # Tanz zählt nicht
    assert build_style_profile(pins, "mode").brands["Adidas Samba"] == 3
    assert build_style_profile(pins, "wohnen").brands["Adidas Samba"] == 0


def test_brand_gets_its_own_search_first():
    pins = [{"title": "", "image_brands": ["Adidas Samba"], "image_categories": ["Schuhe"],
             "image_gender": "herren"} for _ in range(3)]
    assert build_queries(pins, "mode")[0] == ("Herren Adidas Samba", "Schuhe")
    assert build_queries(pins, "mode", ENGLISH)[0] == ("men's Adidas Samba", "Schuhe")


def test_one_pin_is_enough_and_clothing_brands_get_the_item():
    pins = [{"title": "", "image_brands": ["Carhartt"], "image_categories": ["Jacken"],
             "image_gender": "herren"},
            {"title": "", "image_brands": ["Onitsuka Tiger Mexico 66"], "image_categories": ["Schuhe"],
             "image_gender": "herren"},
            {"title": "", "image_brands": ["Ralph Lauren"], "image_categories": ["Oberteile"],
             "image_gender": "herren"},
            {"title": "baggy jeans", "image_gender": "herren"}]
    queries = [q for q, _ in build_queries(pins, "mode")]
    assert len([q for q in queries if any(b in q for b in BRANDS)]) == 2   # max. 2 Marken-Suchen
    assert "Herren Carhartt Jacke" in queries
    assert "Herren Onitsuka Tiger Mexico 66" in queries
    english = [q for q, _ in build_queries(pins[2:], "mode", ENGLISH)]
    assert english[0] == "Ralph Lauren Polo"          # nur 2 Mode-Pins -> kein "men's"
