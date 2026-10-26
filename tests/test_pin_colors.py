"""Tests für die Hauptfarbe aus Pin-Bildern (backend/pin_colors.py)."""

from io import BytesIO

import httpx
from PIL import Image

from backend import pin_colors
from backend.matching import build_style_profile, color_from_hex


def png(background, center, size=100):
    """Testbild: Hintergrund + Quadrat in der Mitte (wie ein Outfit vor einer Wand)."""
    image = Image.new("RGB", (size, size), background)
    image.paste(Image.new("RGB", (size // 2, size // 2), center), (size // 4, size // 4))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_ignores_white_wall_and_finds_the_outfit():
    hex_color = pin_colors.dominant_hex(png("#ffffff", "#d6c1a0"))
    assert color_from_hex(hex_color) == "beige"


def test_black_counts_but_grey_studio_does_not():
    assert color_from_hex(pin_colors.dominant_hex(png("#9a9a9a", "#141414"))) == "schwarz"


def test_only_background_gives_no_color():
    assert pin_colors.dominant_hex(png("#f5f5f5", "#a0a0a0")) is None


def test_fills_only_missing_colors(monkeypatch):
    images = {"https://i.pinimg.com/a.jpg": png("#ffffff", "#b42832")}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=images[str(request.url)])
                                    if str(request.url) in images else httpx.Response(404))
    monkeypatch.setattr(pin_colors, "_http", lambda: httpx.Client(transport=transport))
    pins = [
        {"id": "1", "image_url": "https://i.pinimg.com/a.jpg", "dominant_color": None},
        {"id": "2", "image_url": "https://i.pinimg.com/b.jpg", "dominant_color": "#123456"},  # bleibt
        {"id": "3", "image_url": "https://i.pinimg.com/kaputt.jpg"},                           # 404
    ]
    assert pin_colors.fill_missing_colors(pins) == 1
    assert color_from_hex(pins[0]["dominant_color"]) == "rot"
    assert pins[1]["dominant_color"] == "#123456"
    assert "dominant_color" not in pins[2]
    # Und die Farbe landet im Stilprofil – auch ohne Farbwort im Text
    assert build_style_profile([{"title": "outfit", **pins[0]}]).colors["rot"] == 1
