"""TESTWERKZEUG: Pins eines öffentlichen Pinterest-Boards über dessen RSS-Feed laden.

Solange der API-Zugang von Pinterest noch nicht freigegeben ist, kann man damit
mit ECHTEN Pins testen (Stilprofil, Shop, Malis Vibe, Bilderkennung).

- Nur für öffentliche Boards. Pinterest stellt dafür einen RSS-Feed bereit
  (https://www.pinterest.com/<benutzer>/<board>.rss), wie ihn z.B. Feed-Reader nutzen.
- Kein offiziell dokumentierter Weg und nicht immer zuverlässig -> für die echte App
  bleibt die offizielle API (pins.py). Nur zum Testen verwenden.
- Am besten eigene Boards nutzen (oder von Marken), bei Privatpersonen nur mit Okay.
- Der Feed enthält nur die letzten ~20–25 Pins, ohne Ziel-Link und ohne Bildfarbe.

Starten (auf deinem Mac, nicht in der Cloud):
    python -m backend.rss_import benutzer/board
    python -m backend.rss_import benutzer/board1 benutzer/board2
    python -m backend.rss_import https://www.pinterest.com/benutzer/board.rss
"""

import hashlib
import html
import re
import sys
import time
import xml.etree.ElementTree as ET

import httpx

from backend import pin_colors, storage

FEED_URL = "https://www.pinterest.com/{path}.rss"


def feed_url(source: str) -> str:
    """"benutzer/board" oder eine ganze URL -> RSS-Adresse."""
    if source.startswith(("https://", "http://")):
        return source if source.endswith(".rss") else source.rstrip("/") + ".rss"
    path = source.strip("/")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", path):
        raise ValueError(f"'{source}' bitte als benutzer/board angeben")
    return FEED_URL.format(path=path)


def board_name_from(source: str) -> str:
    """'meinname/herbst-outfits' -> 'herbst outfits' (zählt wie ein Board-Name)."""
    last = source.rstrip("/").removesuffix(".rss").split("/")[-1]
    return last.replace("-", " ")


def strip_html(text: str) -> str:
    """HTML-Schnipsel aus der Beschreibung -> reiner Text."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_feed(xml_text: str, board_name: str) -> list[dict]:
    """RSS-XML -> Pins im selben Format wie pins.py sie speichert."""
    root = ET.fromstring(xml_text)
    pins = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        raw_description = item.findtext("description") or ""
        image = re.search(r'<img[^>]+src="([^"]+)"', raw_description)
        link = (item.findtext("link") or item.findtext("guid") or "").strip()
        description = strip_html(raw_description)
        pins.append({
            # stabile ID aus dem Pin-Link (gleicher Pin = gleiche ID)
            "id": "rss-" + hashlib.sha1(link.encode()).hexdigest()[:12],
            "board_id": "rss",
            "board_name": board_name,
            "title": "" if title == description else title,
            "description": description,
            "alt_text": "",
            "image_url": image.group(1) if image else None,
            "dominant_color": None,
            "link": None,  # der RSS-Link führt zu Pinterest, nicht zum Shop
        })
    return pins


def fetch(source: str) -> list[dict]:
    response = httpx.get(feed_url(source), timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (Malipin-Test; RSS-Reader)"})
    response.raise_for_status()
    return parse_feed(response.text, board_name_from(source))


def main() -> None:
    sources = sys.argv[1:]
    if not sources:
        print(__doc__)
        sys.exit(1)

    all_pins, seen = [], set()
    for source in sources:
        try:
            pins = fetch(source)
        except Exception as err:
            print(f"✗ {source}: konnte nicht geladen werden ({err})")
            continue
        new = [p for p in pins if p["id"] not in seen]
        seen.update(p["id"] for p in new)
        all_pins.extend(new)
        print(f"✓ {source}: {len(new)} Pins")
        for pin in new[:3]:
            print(f"    – {(pin['title'] or pin['description'])[:70]}")

    if not all_pins:
        print("Keine Pins geladen – ist das Board öffentlich und der Name richtig?")
        sys.exit(1)
    # RSS liefert keine Hauptfarbe -> aus den Bildern ausrechnen
    colored = pin_colors.fill_missing_colors(all_pins)
    print(f"Farben aus {colored} Pin-Bildern erkannt.")
    storage.save_pins({"fetched_at": time.time(), "board_ids": ["rss"],
                       "source": "rss-test", "pins": all_pins})
    print(f"\n{len(all_pins)} Pins gespeichert (ersetzt die bisherigen Pins).")
    print("Tipp: Mit Bilderkennung jetzt noch  python -m backend.vision  ausführen.")


if __name__ == "__main__":
    main()
