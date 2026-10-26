"""Schritt 3: Pins der ausgewählten Boards laden und lokal speichern.

Wir speichern pro Pin nur das, was wir fürs Matching brauchen:
ID, Titel, Beschreibung, Bild-URL und die Hauptfarbe, die Pinterest mitliefert.
"""

import time

from backend import pin_colors, pinterest, storage

# Obergrenze pro Board: genug für ein gutes Stilprofil, aber schnell geladen
# und schonend für die Abfragegrenzen (Rate Limits) des Pinterest-Testzugangs.
MAX_PINS_PER_BOARD = 250
# Über alle Boards höchstens so viele Pins analysieren – die neuesten zuerst (zeigen den
# aktuellen Geschmack). Hält Bilderkennung und Shop auch bei riesigen Boards schnell.
MAX_PINS_TOTAL = 500

# Bevorzugte Bildgrößen, in dieser Reihenfolge. 600x ist scharf genug, aber nicht riesig.
IMAGE_SIZES = ["600x", "1200x", "400x300", "originals", "150x150"]


def pick_image_url(media: dict | None) -> str | None:
    """Sucht aus den Bildgrößen eines Pins die passendste URL heraus."""
    if not media:
        return None
    images = media.get("images") or {}
    for size in IMAGE_SIZES:
        if size in images and images[size].get("url"):
            return images[size]["url"]
    # Video-Pins haben kein "images", aber ein Vorschaubild
    return media.get("cover_image_url")


def simplify_pin(pin: dict, board_id: str, board_name: str | None = None) -> dict:
    """Macht aus der großen API-Antwort einen kleinen, übersichtlichen Eintrag."""
    return {
        "id": pin["id"],
        "board_id": board_id,
        # Der Board-Name verrät oft Welt und Stil ("Herbst Outfits", "Wohnzimmer")
        "board_name": board_name,
        "title": pin.get("title") or "",
        "description": pin.get("description") or "",
        # Bildbeschreibung (für Barrierefreiheit) – fehlt oft, hilft aber, wenn vorhanden
        "alt_text": pin.get("alt_text") or "",
        "image_url": pick_image_url(pin.get("media")),
        "dominant_color": pin.get("dominant_color"),
        # Ziel-Link des Pins, z.B. ein Depop-Angebot (siehe shop_links.py)
        "link": pin.get("link"),
        # z.B. "2026-03-01T12:00:00" – für "die neuesten Pins zuerst"
        "created_at": pin.get("created_at"),
    }


def fetch_board_pins(board_id: str, max_pins: int = MAX_PINS_PER_BOARD,
                     board_name: str | None = None) -> list[dict]:
    """Lädt die Pins eines Boards – seitenweise, bis max_pins erreicht sind."""
    pins = []
    bookmark = None
    while len(pins) < max_pins:
        params = {"page_size": 100}
        if bookmark:
            params["bookmark"] = bookmark
        page = pinterest.api_get(f"/boards/{board_id}/pins", params=params)

        for pin in page.get("items", []):
            pins.append(simplify_pin(pin, board_id, board_name))

        bookmark = page.get("bookmark")
        if not bookmark:
            break
    return pins[:max_pins]


def load_pins_for_selected_boards() -> dict:
    """Lädt die Pins aller ausgewählten Boards und speichert sie in data/pins.json."""
    board_ids = storage.load_selected_boards()
    if not board_ids:
        raise ValueError("Keine Boards ausgewählt.")

    # Board-Namen einmal holen: Board-ID -> Name
    board_names = {board["id"]: board["name"] for board in pinterest.list_boards()}

    all_pins = []
    seen_ids = set()  # derselbe Pin kann in mehreren Boards sein -> nur einmal speichern
    for board_id in board_ids:
        for pin in fetch_board_pins(board_id, board_name=board_names.get(board_id)):
            if pin["id"] not in seen_ids:
                seen_ids.add(pin["id"])
                all_pins.append(pin)

    # Zu viele? -> die neuesten behalten (Pins ohne Datum kommen ans Ende)
    if len(all_pins) > MAX_PINS_TOTAL:
        all_pins.sort(key=lambda pin: pin.get("created_at") or "", reverse=True)
        all_pins = all_pins[:MAX_PINS_TOTAL]

    # Pinterest liefert meist eine Hauptfarbe mit – nur fehlende aus dem Bild ausrechnen
    pin_colors.fill_missing_colors(all_pins)
    data = {"fetched_at": time.time(), "board_ids": board_ids, "pins": all_pins}
    storage.save_pins(data)
    return data
