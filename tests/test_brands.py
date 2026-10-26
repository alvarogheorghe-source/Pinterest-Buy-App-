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


def test_single_brand_pin_is_not_enough():
    pins = [{"title": "", "image_brands": ["Carhartt"], "image_categories": ["Jacken"]},
            {"title": "baggy jeans"}]
    assert all("Carhartt" not in q for q, _ in build_queries(pins, "mode"))
