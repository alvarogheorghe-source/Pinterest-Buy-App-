"""Schreibt erfundene Beispiel-Pins nach data/pins.json.

Damit kann man das Matching testen, ohne mit Pinterest verbunden zu sein.
Echte Pins ("Pins laden" in der App) überschreiben die Datei wieder.

Starten mit:  python -m backend.demo_pins
"""

import time

from backend import storage

DEMO_PINS = [
    ("Beige oversized hoodie outfit", "cozy streetwear look for fall"),
    ("Cream knit sweater", "minimalist capsule wardrobe"),
    ("Baggy cargo pants", "street style inspo, olive and black"),
    ("Sand trench coat", "classic timeless outfit"),
    ("Streetwear fit", "oversized tee, white chunky sneakers"),
    ("Neutral tones", "beige, white and camel – clean look"),
    ("Herbst Outfit", "Oversize Pullover in Creme mit weiter Jeans"),
    ("90s vintage denim jacket", "thrifted"),
    ("Black puffer jacket", "winter streetwear"),
    ("Comfy sweatpants look", "grey and beige, athleisure"),
    ("Minimal jewelry", "silver chain"),
    ("Camel coat", "old money style"),
]


def main():
    pins = [
        {"id": f"demo-{i}", "board_id": "demo", "title": title,
         "description": description, "image_url": None, "dominant_color": None}
        for i, (title, description) in enumerate(DEMO_PINS, start=1)
    ]
    storage.save_pins({"fetched_at": time.time(), "board_ids": ["demo"], "pins": pins})
    print(f"{len(pins)} Demo-Pins gespeichert in {storage.DATA_DIR / storage.PINS_FILE}")


if __name__ == "__main__":
    main()
