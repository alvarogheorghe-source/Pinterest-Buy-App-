"""Schreibt erfundene Beispiel-Pins nach data/pins.json.

Damit kann man das Matching testen, ohne mit Pinterest verbunden zu sein.
Echte Pins ("Pins laden" in der App) überschreiben die Datei wieder.

Die Shop-Links sind ebenfalls erfunden und führen zu keinem echten Angebot.

Starten mit:  python -m backend.demo_pins
"""

import time

from backend import storage

# (Titel, Beschreibung, Link)
DEMO_PINS = [
    ("Beige oversized hoodie outfit", "cozy streetwear look for fall", None),
    ("Cream knit sweater", "minimalist capsule wardrobe", None),
    ("Baggy cargo pants", "street style inspo, olive and black – 25€",
     "https://www.depop.com/products/demo-baggy-cargo-pants/"),
    ("Sand trench coat", "classic timeless outfit", None),
    ("Streetwear fit", "oversized tee, white chunky sneakers", None),
    ("Neutral tones", "beige, white and camel – clean look", None),
    ("Herbst Outfit", "Oversize Pullover in Creme mit weiter Jeans, nur 18 €",
     "https://www.vinted.at/items/0000000-demo-oversize-pullover"),
    ("90s vintage denim jacket", "thrifted, £35",
     "https://www.etsy.com/listing/0000000/demo-vintage-denim-jacket"),
    ("Black puffer jacket", "winter streetwear", None),
    ("Comfy sweatpants look", "grey and beige, athleisure",
     "https://www.zalando.at/demo-sweatpants-grau.html"),
    ("Minimal jewelry", "silver chain", "https://demo-schmuck.example.com/products/silberkette"),
    ("Camel coat", "old money style", "https://www.instagram.com/demo/"),  # kein Shop
]


def main():
    pins = [
        {"id": f"demo-{i}", "board_id": "demo", "title": title,
         "description": description, "image_url": None, "dominant_color": None,
         "link": link}
        for i, (title, description, link) in enumerate(DEMO_PINS, start=1)
    ]
    storage.save_pins({"fetched_at": time.time(), "board_ids": ["demo"], "pins": pins})
    print(f"{len(pins)} Demo-Pins gespeichert in {storage.DATA_DIR / storage.PINS_FILE}")


if __name__ == "__main__":
    main()
