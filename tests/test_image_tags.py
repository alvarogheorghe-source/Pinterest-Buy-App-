"""Tests für "Was ist auf dem Pin-Bild?" (backend/image_tags.py) – ohne echtes KI-Modell.

Jeder Beschreibungs-Satz bekommt eine eigene Richtung (Achse). Ein Pin-Bild, das "in
Richtung" goth + Jacke zeigt, muss dann genau diese Begriffe bekommen.
"""

import random

from backend import image_tags, storage, vibe, vision
from backend.matching import CATEGORY_SYNONYMS, STYLE_SYNONYMS, build_style_profile, classify_pin

KEYS = list(image_tags.all_prompts())


def axis(*weights: tuple[str, float]) -> list[float]:
    vector = [0.0] * len(KEYS)
    for key, weight in weights:
        vector[KEYS.index(key)] = weight
    return vision.normalize(vector)


LABELS = {key: axis((key, 1.0)) for key in KEYS}


class FakeTextEmbedder:
    name = "fake-model"

    def __init__(self):
        self.texts = 0

    def embed_texts(self, texts):
        self.texts += len(texts)
        by_text = {text: key for key, group in image_tags.all_prompts().items() for text in group}
        return [LABELS[by_text[text]] for text in texts]


# Vorprüfung: das Bild zeigt Mode bzw. etwas fürs Zuhause
MODE = ("gate:outfit", 1.0)
HOME = ("gate:decor", 1.0)


def test_every_style_and_category_has_a_description():
    assert set(image_tags.STYLE_PROMPTS) == set(STYLE_SYNONYMS)
    assert set(image_tags.CATEGORY_PROMPTS) == set(CATEGORY_SYNONYMS)


def test_clear_image_gets_style_and_category():
    pin = axis(MODE, ("style:goth", 1.0), ("category:Jacken", 1.0))
    assert image_tags.tag(pin, LABELS) == {
        "relevant": True, "department": "mode", "seen": "outfit",
        "styles": ["goth"], "categories": ["Jacken"], "gender": None, "brands": [], "details": []}


def test_two_strong_styles():
    pin = axis(HOME, ("style:boho", 1.0), ("style:natur", 0.995), ("category:Deko", 1.0))
    assert image_tags.tag(pin, LABELS)["styles"] == ["boho", "natur"]


def test_food_photo_gets_no_category_and_unclear_image_nothing():
    food = image_tags.tag(axis(("gate:food", 1.0), ("style:cozy", 1.0)), LABELS)
    assert food["relevant"] is False and food["styles"] == [] and food["categories"] == []
    unclear = vision.normalize([1.0] * len(KEYS))      # passt zu allem gleich wenig
    assert image_tags.tag(unclear, LABELS)["relevant"] is False


def test_desktop_screenshot_is_not_fashion():
    """Bildschirmfoto vom Desktop: keine Stile, keine Kategorie – nichts für Malipin."""
    desktop = image_tags.tag(axis(("gate:desktop", 1.0), ("style:minimalistisch", 1.0),
                                  ("category:Wandgestaltung", 1.0)), LABELS)
    assert desktop == {"relevant": False, "department": None, "seen": "desktop", "styles": [],
                       "categories": [], "gender": None, "brands": [], "details": []}


def test_outfit_in_front_of_a_wall_is_not_wall_art():
    """Erkannte Welt Mode -> Kategorie nur aus Mode, auch wenn das Poster dahinter stark ist."""
    pin = axis(MODE, ("category:Wandgestaltung", 1.0), ("category:Hosen", 0.9))
    assert image_tags.tag(pin, LABELS)["categories"] == ["Hosen"]


def test_pins_without_text_get_a_profile_and_a_vibe(fake):
    pins = [{"id": str(i), "title": "", "image_url": f"https://img.test/{i}.jpg"} for i in range(3)]
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": pins})
    store = vision.EmbeddingStore("fake-model")
    for pin in pins:
        store.put(f"pin:{pin['id']}", pin["image_url"],
                  axis(MODE, ("style:goth", 1.0), ("category:Jacken", 1.0)))

    embedder = FakeTextEmbedder()
    assert image_tags.tag_pins(embedder, store) == 3
    saved = storage.load_pins()["pins"]
    assert saved[0]["image_styles"] == ["goth"] and saved[0]["image_categories"] == ["Jacken"]

    profile = build_style_profile(saved, "mode")
    assert profile.styles["goth"] == 3 and profile.categories["Jacken"] == 3
    assert classify_pin(saved[0]) == {"mode"}                       # Jacke -> Mode, nicht Wohnen
    assert vibe.vibe_check(saved, random.Random(1))["title"] == "Goth Baddie"

    # Sätze werden nur einmal berechnet
    image_tags.tag_pins(embedder, vision.EmbeddingStore("fake-model"))
    assert embedder.texts == len(KEYS) * len(image_tags.TEMPLATES)


def test_outfit_photo_gets_two_categories_and_gender():
    pin = axis(MODE, ("style:casual", 1.0), ("category:Hosen", 1.0), ("category:Oberteile", 0.997),
               ("gender:herren", 1.0))
    result = image_tags.tag(pin, LABELS)
    assert result["categories"] == ["Hosen", "Oberteile"]
    assert result["gender"] == "herren"


def test_no_gender_for_home_decor():
    pin = axis(HOME, ("category:Leuchten", 1.0), ("gender:damen", 1.0))
    assert image_tags.tag(pin, LABELS)["gender"] is None


def test_brand_only_when_clearly_visible():
    sneaker = axis(MODE, ("category:Schuhe", 1.0), ("brand:Adidas Samba", 1.0))
    assert image_tags.tag(sneaker, LABELS)["brands"] == ["Adidas Samba"]
    plain = axis(MODE, ("category:Schuhe", 1.0), ("brand:_plain_shoes", 1.0))
    assert image_tags.tag(plain, LABELS)["brands"] == []
    unsure = axis(MODE, ("category:Schuhe", 1.0), ("brand:Adidas Samba", 1.0),
                  ("brand:Adidas Gazelle", 1.0))
    assert image_tags.tag(unsure, LABELS)["brands"] == []          # 50/50 -> lieber nichts
    lamp = axis(HOME, ("category:Leuchten", 1.0), ("brand:Carhartt", 1.0))
    assert image_tags.tag(lamp, LABELS)["brands"] == []            # Marken nur bei Mode


def test_unsure_what_it_is_and_force():
    """Zufälliges Bild: Mali rät nicht, WAS drauf ist. "Da ist doch ein Fit drauf" -> Mode."""
    unclear = vision.normalize([1.0] * len(KEYS))
    assert image_tags.tag(unclear, LABELS)["seen"] is None
    forced = image_tags.tag(axis(("gate:animal", 1.0), ("category:Jacken", 1.0)), LABELS, force=True)
    assert forced["relevant"] is True and forced["department"] == "mode"


def test_details_in_the_image():
    """Jeans auf dem Bild, klar Bootcut + Light Wash -> beide Merkmale; Schnitt unklar -> keiner."""
    pin = axis(MODE, ("category:Hosen", 1.0), ("detail:Hosen|Bootcut", 1.0),
               ("detail:Hosen|Light Wash", 1.0), ("detail:Hosen|Jeans", 1.0))
    found = image_tags.tag(pin, LABELS)
    assert found["categories"] == ["Hosen"]
    assert {tuple(d) for d in found["details"]} == {("Hosen", "Bootcut"), ("Hosen", "Light Wash"),
                                                    ("Hosen", "Jeans")}
    # Gleich stark Bootcut und Skinny -> kein Schnitt (lieber nichts als falsch)
    unsure = axis(MODE, ("category:Hosen", 1.0), ("detail:Hosen|Bootcut", 1.0),
                  ("detail:Hosen|Skinny", 1.0))
    assert image_tags.tag(unsure, LABELS)["details"] == []
    # "ganz normal" gewinnt -> kein Muster
    plain = axis(MODE, ("category:Oberteile", 1.0), ("detail:Oberteile|_muster", 1.0))
    assert image_tags.tag(plain, LABELS)["details"] == []


def test_image_details_shape_the_search():
    """Pins ohne Text, nur Bild-Erkennung -> genaue Suche "Bootcut Light Wash Jeans"."""
    from backend.search_queries import build_queries
    pins = [{"id": str(i), "title": "", "image_categories": ["Hosen"],
             "image_details": [["Hosen", "Jeans"], ["Hosen", "Bootcut"], ["Hosen", "Light Wash"]]}
            for i in range(3)]
    texts = [q for q, _ in build_queries(pins, "mode")]
    assert any("Bootcut" in t and "Light Wash" in t and t.endswith("Jeans") for t in texts)


def test_every_detail_prompt_is_a_sensible_phrase():
    assert image_tags.DETAIL_PROMPTS["Hosen|Bootcut"] == "bootcut pants"
    assert image_tags.DETAIL_PROMPTS["Hosen|Mom Jeans"] == "mom jeans"
    assert image_tags.DETAIL_PROMPTS["Schuhe|Low Top"] == "low top shoes"
    assert image_tags.DETAIL_PROMPTS["Schuhe|Chelsea Boots"] == "chelsea boots"


def test_gender_from_two_views_of_the_same_photo():
    herren, damen = axis(("gender:herren", 1.0)), axis(("gender:damen", 1.0))
    assert image_tags.gender_of([herren, herren], LABELS) == "herren"
    assert image_tags.gender_of([herren, damen], LABELS) is None       # uneinig -> nicht raten
