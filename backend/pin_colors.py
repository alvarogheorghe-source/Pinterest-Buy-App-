"""Hauptfarbe eines Pins aus dem Bild ausrechnen – wenn Pinterest keine mitliefert.

Über die offizielle Pinterest-API kommt zu jedem Pin "dominant_color" mit. Beim RSS-Test-
Import (backend/rss_import.py) fehlt sie – dann fehlen im Stilprofil die Farben, wenn im
Pin-Text keine Farbwörter stehen. Diese Datei füllt die Lücke:

1. Pin-Bild laden (klein), nur die Bildmitte nehmen (dort ist meist das Outfit/Objekt)
2. Weiße und graue Pixel überspringen (Wand, Studio-Hintergrund)
3. Ähnliche Farben in "Eimer" sortieren; der vollste Eimer ist die Hauptfarbe

Läuft lokal, kostet nichts. Braucht Pillow (steht in requirements.txt).

Für bereits gespeicherte Pins nachträglich:   python -m backend.pin_colors
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import httpx

from backend import storage

MAX_BYTES = 5 * 1024 * 1024   # größere Bilder überspringen
WORKERS = 8                    # so viele Bilder gleichzeitig laden


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests das Laden simulieren können."""
    return httpx.Client(timeout=10, follow_redirects=True)


def is_background(r: int, g: int, b: int) -> bool:
    """Gleiche Regeln wie matching.color_from_hex: fast weiß oder grau = Hintergrund."""
    brightest, darkest = max(r, g, b), min(r, g, b)
    return darkest > 225 or (brightest - darkest < 18 and brightest > 60)


def dominant_hex(image_bytes: bytes) -> str | None:
    """Bild -> "#rrggbb" der Hauptfarbe. None, wenn das Bild nur Hintergrund zeigt."""
    from PIL import Image  # erst hier: ohne Pillow läuft der Rest der App trotzdem

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((64, 64))
    w, h = image.size
    image = image.crop((w // 5, h // 5, w - w // 5, h - h // 5))   # mittlere 60 %

    buckets: Counter = Counter()
    members: dict[tuple, list] = {}
    for pixel in image.getdata():
        if is_background(*pixel):
            continue
        key = tuple(c // 32 for c in pixel)        # 8 Stufen pro Farbkanal
        buckets[key] += 1
        members.setdefault(key, []).append(pixel)
    if not buckets:
        return None
    best = members[buckets.most_common(1)[0][0]]
    r, g, b = (sum(channel) // len(best) for channel in zip(*best))
    return f"#{r:02x}{g:02x}{b:02x}"


def _color_for(pin: dict) -> str | None:
    url = pin.get("image_url")
    if not url or not url.startswith("https://"):
        return None
    try:
        with _http() as client:
            response = client.get(url)
        if response.status_code != 200 or len(response.content) > MAX_BYTES:
            return None
        return dominant_hex(response.content)
    except Exception:   # kaputtes Bild, Netzwerkfehler … -> einfach ohne Farbe weiter
        return None


def fill_missing_colors(pins: list[dict]) -> int:
    """Setzt "dominant_color" bei allen Pins, die keine haben. Gibt die Anzahl zurück."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Hinweis: Pillow fehlt – Farben aus Bildern übersprungen (pip install -r requirements.txt)")
        return 0
    missing = [pin for pin in pins if not pin.get("dominant_color") and pin.get("image_url")]
    with ThreadPoolExecutor(WORKERS) as pool:
        colors = list(pool.map(_color_for, missing))
    for pin, color in zip(missing, colors):
        if color:
            pin["dominant_color"] = color
    return sum(1 for color in colors if color)


def main() -> None:
    data = storage.load_pins()
    if not data["pins"]:
        print("Noch keine Pins gespeichert.")
        return
    found = fill_missing_colors(data["pins"])
    storage.save_pins(data)
    print(f"Farben aus {found} Pin-Bildern erkannt ({len(data['pins'])} Pins insgesamt).")


if __name__ == "__main__":
    main()
