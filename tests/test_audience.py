"""Herren- oder Damenmode? (matching.audience) – für passendere Suchen und Vibes."""

import random

from backend import vibe
from backend.matching import audience
from backend.search_queries import ENGLISH, build_queries


def pins(n, **extra):
    return [{"title": "baggy jeans outfit", **extra} for _ in range(n)]


def test_audience_from_images_and_text():
    assert audience(pins(4, image_gender="herren")) == "herren"
    assert audience(pins(2, image_gender="herren")) is None                  # zu wenig Pins
    assert audience(pins(3, image_gender="herren") + pins(3, image_gender="damen")) is None
    assert audience([{"title": "women's summer dress"} for _ in range(3)]) == "damen"
    assert audience([{"title": "was man im Herbst trägt: Jacke"} for _ in range(3)]) is None


def test_searches_get_herren_or_damen():
    board = pins(4, image_gender="herren", image_styles=["oversized"], image_categories=["Hosen"])
    assert build_queries(board, "mode")[0] == ("Herren Baggy Jeans", "Hosen")
    assert build_queries(board, "mode", ENGLISH)[0] == ("men's baggy jeans", "Hosen")
    assert not build_queries(board, "wohnen")[0][0].startswith("Herren")    # Wohnen: egal


def test_mens_board_gets_a_neutral_vibe():
    board = pins(5, image_gender="herren", image_styles=["casual", "oversized"],
                 image_categories=["Hosen"])
    assert vibe.vibe_check(board, random.Random(1))["title"] == "Effortless Cool"
    clean = [{"title": "minimal clean white outfit", "image_gender": "herren",
              "image_categories": ["Oberteile"]} for _ in range(4)]
    assert vibe.vibe_check(clean, random.Random(1))["title"] == "Clean Fit"
    # Ohne Herren-Hinweis bleibt "Clean Girl" möglich
    girl = [{"title": "minimal clean girl outfit white"} for _ in range(4)]
    assert vibe.vibe_check(girl, random.Random(1))["title"] == "Clean Girl"
