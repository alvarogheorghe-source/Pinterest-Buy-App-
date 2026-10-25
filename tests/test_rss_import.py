"""Tests für das RSS-Testwerkzeug (backend/rss_import.py) – mit einem Beispiel-Feed,
ohne Internet.

Starten mit:  pytest -v
"""

import pytest

from backend import rss_import, storage

SAMPLE_FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <title>Herbst Outfits</title>
  <item>
    <title>Beige oversized hoodie</title>
    <link>https://www.pinterest.com/pin/111/</link>
    <description>&lt;a href="/pin/111/"&gt;&lt;img src="https://i.pinimg.com/236x/aa/hoodie.jpg"&gt;&lt;/a&gt;Cozy streetwear look &amp;amp; cream knit</description>
    <guid>https://www.pinterest.com/pin/111/</guid>
  </item>
  <item>
    <title></title>
    <link>https://www.pinterest.com/pin/222/</link>
    <description>&lt;a href="/pin/222/"&gt;&lt;img src="https://i.pinimg.com/236x/bb/dress.jpg"&gt;&lt;/a&gt;</description>
  </item>
</channel></rss>"""


def test_feed_url():
    assert rss_import.feed_url("meinname/herbst-outfits") == \
        "https://www.pinterest.com/meinname/herbst-outfits.rss"
    assert rss_import.feed_url("https://www.pinterest.com/a/b/") == "https://www.pinterest.com/a/b.rss"
    with pytest.raises(ValueError):
        rss_import.feed_url("nur-ein-name")
    with pytest.raises(ValueError):
        rss_import.feed_url("../../etc/passwd")


def test_parse_feed_gives_pins_like_the_api():
    pins = rss_import.parse_feed(SAMPLE_FEED, rss_import.board_name_from("meinname/herbst-outfits"))
    assert len(pins) == 2
    first = pins[0]
    assert first["title"] == "Beige oversized hoodie"
    assert first["description"] == "Cozy streetwear look & cream knit"   # HTML entfernt
    assert first["image_url"] == "https://i.pinimg.com/236x/aa/hoodie.jpg"
    assert first["board_name"] == "herbst outfits"
    assert first["link"] is None                     # führt nicht zu einem Shop
    assert first["id"].startswith("rss-") and first["id"] != pins[1]["id"]
    assert pins[1]["title"] == "" and pins[1]["description"] == ""
    # Gleicher Feed -> gleiche IDs (wichtig für Bilderkennung, die nach ID speichert)
    assert [p["id"] for p in rss_import.parse_feed(SAMPLE_FEED, "x")] == [p["id"] for p in pins]


def test_imported_pins_work_with_the_rest_of_the_app(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["rss"],
                       "pins": rss_import.parse_feed(SAMPLE_FEED, "herbst outfits")})
    profile = client.get("/api/profile").json()["mode"]
    assert "beige" in profile["top_colors"] and "streetwear" in profile["top_styles"]
    assert client.get("/api/vibe").json()["pin_count"] == 2
    assert client.get("/api/recommendations").json()["products"][0]["score"] > 0
