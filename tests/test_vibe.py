"""Tests für Malis Vibe-Check (backend/vibe.py).

Starten mit:  pytest -v
"""

import random

from backend import matching, storage, vibe


def pins(*titles):
    return [{"title": t, "description": ""} for t in titles]


def test_goth_pins_give_goth_baddie():
    result = vibe.vibe_check(pins("Gothic outfit black lace", "witchy vibes", "dark aesthetic"),
                             random.Random(0))
    assert result["title"] == "Goth Baddie" and result["emoji"] == "🖤"
    assert result["text"] in vibe.VIBES[0].lines
    assert result["pin_count"] == 3


def test_other_vibes():
    assert vibe.vibe_check(pins("oversized streetwear hoodie", "baggy cargo street style"))[
        "title"] == "Streetwear-Ikone"
    assert vibe.vibe_check(pins("coquette bows", "pink ballet flats, romantic"))[
        "title"] == "Coquette-Darling"
    assert vibe.vibe_check(pins("Japandi living room", "scandi wood"))["title"] == "Japandi-Ruhepol"


def test_second_vibe_when_close():
    result = vibe.vibe_check(pins("goth black", "goth outfit", "y2k glitter", "y2k pink"))
    assert result["title"] == "Goth Baddie"
    assert result["second"] == "💿 Y2K-Icon"


def test_no_pins_and_unclear_pins():
    assert vibe.vibe_check([])["title"] == "Noch ein Geheimnis"
    assert vibe.vibe_check(pins("fit 🤍", "inspo"))["title"] == "Einzigartiges Unikat"


def test_lines_vary_with_random():
    goth = pins("gothic", "goth")
    lines = {vibe.vibe_check(goth, random.Random(seed))["text"] for seed in range(20)}
    assert len(lines) > 1   # nicht immer derselbe Spruch


def test_every_vibe_term_is_known_and_lines_stay_positive():
    known = set(matching.STYLE_SYNONYMS) | set(matching.COLOR_SYNONYMS)
    negative = ["hässlich", "schlecht", "langweilig", "peinlich", "dick", "fett", "leider"]
    for v in vibe.VIBES + [vibe.UNIQUE, vibe.NO_PINS]:
        assert set(v.terms) <= known, v.title          # Tippfehler würden nie zählen
        assert v.lines, v.title
        for line in v.lines:
            assert not any(word in line.lower() for word in negative), line


def test_api_vibe(fake, client):
    assert client.get("/api/vibe").json()["title"] == "Noch ein Geheimnis"
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": pins("gothic", "goth")})
    result = client.get("/api/vibe").json()
    assert result["title"] == "Goth Baddie"
    assert set(result) == {"title", "emoji", "text", "second", "terms", "pin_count"}
