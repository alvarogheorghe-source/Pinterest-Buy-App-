"""Tests für Schritt 5: Stilprofil und Produkt-Ranking.

Starten mit:  pytest -v
"""

from backend import matching, storage
from backend.matching import build_style_profile, find_terms, rank_products
from backend.products import JsonProductSource
from tests.test_products import make_product


def pin(title="", description=""):
    return {"title": title, "description": description}


# --- Wörter finden ---------------------------------------------------------------------

def test_synonyms_in_german_and_english():
    assert find_terms("Black oversized hoodie", matching.COLOR_PATTERNS) == {"schwarz"}
    assert find_terms("Cream knit, baggy fit", matching.COLOR_PATTERNS) == {"beige"}
    assert find_terms("Cream knit, baggy fit", matching.STYLE_PATTERNS) == {"oversized"}
    assert find_terms("Lässiges Outfit in Weiß", matching.COLOR_PATTERNS) == {"weiß"}


def test_word_boundaries_prevent_false_hits():
    # "red" steckt in "redesign", "rot" in "Brot" – beides darf NICHT zählen
    assert find_terms("Redesign mit Brot", matching.COLOR_PATTERNS) == set()


def test_hashtags_and_case_are_found():
    assert find_terms("#STREETWEAR #Y2K", matching.STYLE_PATTERNS) == {"streetwear", "y2k"}


def test_every_product_term_is_known():
    """Jede Farbe/jeder Tag aus products.json muss in den Synonym-Listen stehen,
    sonst könnte das Produkt nie gematcht werden."""
    for product in JsonProductSource().load():
        for color in product.colors:
            assert color in matching.COLOR_SYNONYMS, f"{product.id}: {color}"
        for tag in product.style_tags:
            assert tag in matching.STYLE_SYNONYMS, f"{product.id}: {tag}"


# --- Stilprofil ------------------------------------------------------------------------------

def test_profile_counts_each_term_once_per_pin():
    profile = build_style_profile([
        pin("beige beige beige", "beige streetwear"),  # beige nur 1x gezählt
        pin("Beige oversized look"),
        pin("Black street style"),
    ])
    assert profile.pin_count == 3
    assert profile.colors == {"beige": 2, "schwarz": 1}
    assert profile.styles == {"streetwear": 2, "oversized": 1}
    assert profile.to_dict()["top_colors"] == ["beige", "schwarz"]


def test_empty_profile():
    profile = build_style_profile([])
    assert profile.pin_count == 0
    assert profile.weight("beige") == 0.0


# --- Ranking ---------------------------------------------------------------------------------

def test_best_match_first_and_cheaper_wins_ties():
    profile = build_style_profile([pin("beige oversized"), pin("beige"), pin("streetwear")])
    items = [
        make_product(id="nix", colors=["rot"], style_tags=["elegant"], price=5),
        make_product(id="beige-teuer", colors=["beige"], style_tags=[], price=50),
        make_product(id="beige-billig", colors=["beige"], style_tags=[], price=20),
        make_product(id="top", colors=["beige"], style_tags=["oversized"], price=60),
    ]
    ranked = rank_products(items, profile)
    assert [r["id"] for r in ranked] == ["top", "beige-billig", "beige-teuer", "nix"]
    assert ranked[0]["matched"] == ["beige", "oversized"]  # häufigster Begriff zuerst
    assert ranked[-1]["score"] == 0


def test_reason_sentences():
    profile = build_style_profile([pin("beige oversized"), pin("beige")])
    two, one, none = rank_products([
        make_product(id="a", colors=["beige"], style_tags=["oversized"]),
        make_product(id="b", colors=["beige"], style_tags=[]),
        make_product(id="c", colors=["rot"], style_tags=[]),
    ], profile)
    assert two["reason"] == ("Passt zu dir, weil beige (2 Pins) und oversized (1 Pin) "
                             "oft in deinen Pins vorkommen.")
    assert one["reason"] == "Passt zu dir, weil beige (2 Pins) oft in deinen Pins vorkommt."
    assert none["reason"].startswith("Kein direkter Treffer")


# --- API ---------------------------------------------------------------------------------------

def test_api_recommendations_use_saved_pins_and_budget(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        pin("Beige oversized hoodie", "streetwear"),
        pin("cream streetwear fit"),
    ]})
    result = client.get("/api/recommendations?max_price=40").json()

    assert result["profile"]["top_colors"] == ["beige"]
    top = result["products"][0]
    assert top["name"] == "Oversized Hoodie Sand"  # beige + oversized + streetwear
    assert top["reason"].startswith("Passt zu dir")
    assert all(p["price"] <= 40 for p in result["products"])


def test_api_profile_without_pins(fake, client):
    profiles = client.get("/api/profile").json()
    assert profiles["mode"]["pin_count"] == 0
    assert profiles["wohnen"]["pin_count"] == 0


# --- Mode und Wohnen trennen -----------------------------------------------------------------

def test_every_product_category_is_known():
    """Jede Kategorie aus products.json braucht eine Wortliste in der richtigen Welt."""
    for product in JsonProductSource().load():
        assert product.category in matching.CATEGORY_SYNONYMS, product.category
        assert matching.CATEGORY_SYNONYMS[product.category][0] == product.department


def test_categories_are_found_with_plural():
    found = find_terms("Ceramic vases and two lamps on a shelf", matching.CATEGORY_PATTERNS)
    assert found == {"Deko", "Leuchten", "Möbel"}
    assert find_terms("Baggy jeans + white sneakers", matching.CATEGORY_PATTERNS) == {
        "Hosen", "Schuhe"}
    assert find_terms("Tee am Morgen", matching.CATEGORY_PATTERNS) == set()  # Getränk!


def test_german_compound_words():
    found = find_terms("Keramikvase, Stehlampe und Blumentopf", matching.CATEGORY_PATTERNS)
    assert found == {"Deko", "Leuchten", "Pflanzen & Töpfe"}
    assert find_terms("Regenjacke und Jogginghose", matching.CATEGORY_PATTERNS) == {
        "Jacken", "Hosen"}
    # Diese Fallen dürfen NICHT erkannt werden:
    for text in ["Praktisch für den Laptop", "Entdecke praktische Ideen", "Barock-Stil",
                 "Vom Hersteller", "im Rahmen des Projekts"]:
        assert find_terms(text, matching.CATEGORY_PATTERNS) == set(), text
    assert find_terms("Strickdecke und Minirock", matching.CATEGORY_PATTERNS) == {
        "Textilien", "Kleider & Röcke"}


def test_classify_pin():
    assert matching.classify_pin(pin("Beige oversized hoodie")) == {"mode"}
    assert matching.classify_pin(pin("Japandi living room")) == {"wohnen"}
    assert matching.classify_pin(pin("Keramikvase", "minimalistisch")) == {"wohnen"}
    assert matching.classify_pin(pin("Outfit mit Vase als Requisite")) == {"mode", "wohnen"}
    assert matching.classify_pin(pin("Neutral tones beige")) == {"mode", "wohnen"}  # unklar


def test_profiles_are_separated_by_department():
    pins = [
        pin("Streetwear outfit", "black hoodie"),          # nur Mode
        pin("Japandi living room", "beige linen sofa"),    # nur Wohnen
        pin("Ceramic vase", "minimal, sand"),              # nur Wohnen
        pin("Neutral tones", "beige and cream"),           # beide
    ]
    mode = build_style_profile(pins, "mode")
    home = build_style_profile(pins, "wohnen")

    assert mode.pin_count == 2 and home.pin_count == 3
    assert "streetwear" in mode.styles and "streetwear" not in home.styles
    assert "japandi" in home.styles and "japandi" not in mode.styles
    assert mode.categories == {"Oberteile": 1}
    assert home.categories == {"Möbel": 1, "Deko": 1}
    assert home.colors["beige"] == 3


def test_category_bonus_in_ranking():
    profile = build_style_profile([pin("vase"), pin("vases on a shelf"), pin("beige")], "wohnen")
    ranked = rank_products([
        make_product(id="kissen", department="wohnen", category="Textilien", colors=["beige"]),
        make_product(id="vase", department="wohnen", category="Deko", colors=["beige"]),
    ], profile)
    assert [r["id"] for r in ranked] == ["vase", "kissen"]
    assert ranked[0]["reason"] == ("Passt zu dir, weil Deko (2 Pins) und beige (1 Pin) "
                                   "oft in deinen Pins vorkommen.")


def test_api_recommendations_per_department(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        pin("Ceramic vase", "japandi, sand"),
        pin("Japandi bedroom", "linen and wood"),
        pin("Streetwear outfit", "beige oversized hoodie"),
    ]})
    home = client.get("/api/recommendations?department=wohnen").json()
    assert home["profile"]["pin_count"] == 2
    assert all(p["department"] == "wohnen" for p in home["products"])
    assert home["products"][0]["name"] == "Keramikvase Sand"

    fashion = client.get("/api/recommendations").json()  # Standard: Mode
    assert all(p["department"] == "mode" for p in fashion["products"])
    assert fashion["products"][0]["name"] == "Oversized Hoodie Sand"
