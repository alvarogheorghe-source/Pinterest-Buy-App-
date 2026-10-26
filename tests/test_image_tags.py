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
        by_text = {text: key for key, text in image_tags.all_prompts().items()}
        return [LABELS[by_text[text]] for text in texts]


def test_every_style_and_category_has_a_description():
    assert set(image_tags.STYLE_PROMPTS) == set(STYLE_SYNONYMS)
    assert set(image_tags.CATEGORY_PROMPTS) == set(CATEGORY_SYNONYMS)


def test_clear_image_gets_style_and_category():
    pin = axis(("style:goth", 1.0), ("category:Jacken", 1.0))
    assert image_tags.tag(pin, LABELS) == {"styles": ["goth"], "categories": ["Jacken"], "gender": None}


def test_two_strong_styles():
    pin = axis(("style:boho", 1.0), ("style:natur", 0.995), ("category:Deko", 1.0))
    assert image_tags.tag(pin, LABELS)["styles"] == ["boho", "natur"]


def test_food_photo_gets_no_category_and_unclear_image_nothing():
    assert image_tags.tag(axis(("category:_food", 1.0)), LABELS)["categories"] == []
    unclear = vision.normalize([1.0] * len(KEYS))      # passt zu allem gleich wenig
    assert image_tags.tag(unclear, LABELS) == {"styles": [], "categories": [], "gender": None}


def test_pins_without_text_get_a_profile_and_a_vibe(fake):
    pins = [{"id": str(i), "title": "", "image_url": f"https://img.test/{i}.jpg"} for i in range(3)]
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": pins})
    store = vision.EmbeddingStore("fake-model")
    for pin in pins:
        store.put(f"pin:{pin['id']}", pin["image_url"], axis(("style:goth", 1.0), ("category:Jacken", 1.0)))

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
    assert embedder.texts == len(KEYS)


def test_outfit_photo_gets_two_categories_and_gender():
    pin = axis(("style:casual", 1.0), ("category:Hosen", 1.0), ("category:Oberteile", 0.997),
               ("gender:herren", 1.0))
    result = image_tags.tag(pin, LABELS)
    assert result["categories"] == ["Hosen", "Oberteile"]
    assert result["gender"] == "herren"


def test_no_gender_for_home_decor():
    pin = axis(("category:Leuchten", 1.0), ("gender:damen", 1.0))
    assert image_tags.tag(pin, LABELS)["gender"] is None
