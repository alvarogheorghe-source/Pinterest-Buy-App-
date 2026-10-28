"""Stil-Lexikon (backend/style_guide.py): jeder Vibe und jeder Stil hat eine Erklärung."""

from backend import style_guide, vibe
from backend.matching import STYLE_SYNONYMS


def test_every_vibe_and_style_is_explained():
    assert set(style_guide.VIBE_TEXTS) == {v.title for v in vibe.VIBES} | {vibe.UNIQUE.title}
    assert set(style_guide.STYLE_TEXTS) == set(STYLE_SYNONYMS)


def test_guide_links_vibes_and_styles_both_ways():
    data = style_guide.guide("de")
    vibes = {v["slug"]: v for v in data["vibes"]}
    styles = {s["slug"]: s for s in data["styles"]}
    goth = vibes["vibe-goth-baddie"]
    assert {s["slug"] for s in goth["styles"]} == {"stil-goth", "stil-grunge"}
    assert goth["colors"] == ["#1e1e1e"] and goth["pieces"]
    assert "vibe-goth-baddie" in {v["slug"] for v in styles["stil-goth"]["vibes"]}
    # Jede Verknüpfung zeigt auf einen Eintrag, den es wirklich gibt
    for v in data["vibes"]:
        assert all(s["slug"] in styles for s in v["styles"])
    for s in data["styles"]:
        assert all(v["slug"] in vibes for v in s["vibes"])


def test_english(client):
    client.cookies.set("lang", "en")
    data = client.get("/api/styles").json()
    clean = next(v for v in data["vibes"] if v["slug"] == "vibe-clean-girl")
    assert clean["pieces"][0] == "White tank top"
    assert next(s for s in data["styles"] if s["slug"] == "stil-sportlich")["name"] == "Sporty"
