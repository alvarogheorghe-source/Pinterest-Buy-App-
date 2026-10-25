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
    assert client.get("/api/profile").json()["pin_count"] == 0
