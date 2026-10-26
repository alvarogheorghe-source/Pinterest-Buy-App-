"""Marken und Modelle, die die App in Pins erkennen kann (Bild UND Text).

Jede Marke hat:
- category: wohin sie gehört ("Schuhe", "Jacken", …) – für die Suche bei eBay/Etsy
- prompt:   Beschreibung fürs Bild (FashionCLIP, Englisch), siehe image_tags.py
- words:    Wörter im Pin-Text, z.B. "samba" oder "af1"

Bilderkennung von Marken klappt am besten bei Teilen mit typischer Form oder großem Logo
(Sneaker!). Bei schlichten Basics ohne Logo kann kein Modell die Marke sicher sehen – darum
zählen nur sehr sichere Treffer (image_tags.BRAND_MIN).

Neue Marke? Einfach unten eintragen – Bild- und Textsuche nutzen sie automatisch.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Brand:
    category: str
    prompt: str
    words: tuple[str, ...]


BRANDS = {
    # Sneaker & Schuhe – typische Formen, gut erkennbar
    "Nike Air Force 1": Brand("Schuhe", "Nike Air Force 1 white leather sneakers",
                              ("air force 1", "air force one", "af1")),
    "Nike Dunk": Brand("Schuhe", "Nike Dunk Low sneakers", ("nike dunk", "dunk low", "dunks")),
    "Nike Air Max": Brand("Schuhe", "Nike Air Max sneakers with visible air bubble",
                          ("air max", "airmax")),
    "Adidas Samba": Brand("Schuhe", "Adidas Samba sneakers with gum sole",
                          ("adidas samba", "sambas", "samba og")),
    "Adidas Gazelle": Brand("Schuhe", "Adidas Gazelle suede sneakers", ("adidas gazelle", "gazelles")),
    "Adidas Superstar": Brand("Schuhe", "Adidas Superstar shell toe sneakers", ("adidas superstar",)),
    "New Balance 550": Brand("Schuhe", "New Balance 550 basketball sneakers",
                             ("new balance 550", "nb550")),
    "New Balance 530": Brand("Schuhe", "New Balance 530 silver running sneakers",
                             ("new balance 530", "nb530")),
    "Converse Chuck Taylor": Brand("Schuhe", "Converse Chuck Taylor All Star canvas sneakers",
                                   ("converse", "chuck taylor", "chucks")),
    "Vans Old Skool": Brand("Schuhe", "Vans Old Skool sneakers with side stripe",
                            ("old skool", "vans")),
    "Onitsuka Tiger Mexico 66": Brand("Schuhe", "Onitsuka Tiger Mexico 66 sneakers",
                                      ("onitsuka", "mexico 66")),
    "Asics Gel": Brand("Schuhe", "Asics Gel running sneakers", ("asics",)),
    "Salomon XT-6": Brand("Schuhe", "Salomon XT-6 trail running sneakers", ("salomon", "xt-6", "xt6")),
    "Dr. Martens": Brand("Schuhe", "Dr. Martens black leather boots with yellow stitching",
                         ("dr. martens", "dr martens", "doc martens")),
    "Birkenstock Boston": Brand("Schuhe", "Birkenstock Boston suede clogs",
                                ("birkenstock", "boston clog")),
    "UGG": Brand("Schuhe", "UGG sheepskin boots", ("ugg", "uggs")),
    # Kleidung – nur mit deutlichem Logo oder Schnitt
    "Carhartt": Brand("Jacken", "a Carhartt workwear jacket with logo patch", ("carhartt",)),
    "The North Face": Brand("Jacken", "The North Face puffer jacket", ("north face", "tnf", "nuptse")),
    "Arc'teryx": Brand("Jacken", "an Arc'teryx shell jacket with bird logo", ("arcteryx", "arc'teryx")),
    "Patagonia": Brand("Jacken", "a Patagonia fleece jacket", ("patagonia",)),
    "Stüssy": Brand("Oberteile", "a Stussy logo t-shirt or hoodie", ("stussy", "stüssy")),
    "Ralph Lauren": Brand("Oberteile", "a Ralph Lauren polo shirt with pony logo",
                          ("ralph lauren", "polo ralph")),
}

# Gegenstücke "keine Marke erkennbar" – gewinnt eines davon, zählt keine Marke
NO_BRAND_PROMPTS = {
    "_plain_shoes": "plain shoes without a visible brand",
    "_plain_clothes": "plain clothes without a visible logo",
    "_outfit": "a casual outfit",
}
