"""Erzeugt eigene Platzhalterbilder (PNG) für die Beispielprodukte.

Warum eigene Bilder statt eines Online-Dienstes?
- Die Bilderkennung (FashionCLIP) kann PNG lesen (der Dienst lieferte SVG).
- Funktioniert ohne Internet.
- Datenschutz: Der Browser muss keine fremde Website kontaktieren.

Braucht Pillow:  pip install pillow
Starten:         python scripts/make_placeholders.py
Ergebnis:        frontend/img/products/<produkt-id>.png  (+ passt products.json an)
"""

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "data" / "products.json"
OUT = ROOT / "frontend" / "img" / "products"
SIZE = (600, 750)

# Farbname -> RGB (Hauptfarbe = erste Farbe des Produkts)
COLORS = {
    "beige": (216, 195, 165), "weiß": (242, 240, 236), "schwarz": (40, 36, 38),
    "grau": (158, 158, 158), "braun": (123, 90, 60), "blau": (143, 179, 217),
    "grün": (122, 158, 126), "oliv": (107, 112, 72), "rosa": (232, 180, 188),
    "rot": (180, 40, 50), "orange": (200, 105, 63), "gelb": (225, 190, 60),
    "silber": (192, 192, 192), "gold": (201, 165, 74),
}

# Erste vorhandene Schrift nehmen (Linux, Mac), sonst die eingebaute
FONT_FILES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def font(size: int):
    from PIL import ImageFont
    for path in FONT_FILES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_image(name: str, category: str, color: tuple[int, int, int]):
    # Pillow erst hier laden: so können andere Dateien COLORS nutzen, ohne Pillow zu brauchen
    from PIL import Image, ImageDraw
    image = Image.new("RGB", SIZE, color)
    draw = ImageDraw.Draw(image)
    # Sanfter Verlauf: oben etwas heller, unten etwas dunkler
    for y in range(SIZE[1]):
        f = 1.12 - 0.24 * y / SIZE[1]
        draw.line([(0, y), (SIZE[0], y)], fill=tuple(min(255, int(c * f)) for c in color))
    # Helle Farben -> dunkle Schrift, dunkle Farben -> helle Schrift
    text_color = (60, 42, 48) if sum(color) > 400 else (255, 250, 246)
    draw.text((SIZE[0] / 2, 300), category.upper(), font=font(26), fill=text_color, anchor="mm")
    lines = textwrap.wrap(name, width=16)
    for i, line in enumerate(lines):
        draw.text((SIZE[0] / 2, 370 + i * 52), line, font=font(44), fill=text_color, anchor="mm")
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    for product in data["products"]:
        color = COLORS.get(product["colors"][0], (230, 220, 220))
        make_image(product["name"], product["category"], color).save(
            OUT / f"{product['id']}.png", optimize=True)
        product["image_url"] = f"/img/products/{product['id']}.png"
    PRODUCTS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(data['products'])} Bilder erzeugt in {OUT}")


if __name__ == "__main__":
    main()
