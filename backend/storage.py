"""Einfache Datenspeicherung in JSON-Dateien im Ordner data/.

Für den Prototyp reicht das völlig. Später kann man das durch SQLite
ersetzen, ohne den Rest der App zu ändern.
"""

import json
from pathlib import Path

from backend.config import BASE_DIR

# Als Variable, damit Tests einen Temp-Ordner unterschieben können
DATA_DIR = BASE_DIR / "data"


def _path(filename: str) -> Path:
    return DATA_DIR / filename


def read_json(filename: str, default=None):
    """Liest eine JSON-Datei. Gibt `default` zurück, wenn sie nicht existiert."""
    path = _path(filename)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(filename: str, data) -> None:
    """Schreibt Daten als schön formatiertes JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _path(filename).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_json(filename: str) -> None:
    _path(filename).unlink(missing_ok=True)


# --- Tokens -----------------------------------------------------------------
# Wir speichern NUR die OAuth-Tokens von Pinterest – keine Passwörter, keine Cookies.

TOKEN_FILE = "tokens.json"


def load_tokens() -> dict | None:
    return read_json(TOKEN_FILE)


def save_tokens(tokens: dict) -> None:
    write_json(TOKEN_FILE, tokens)


def delete_tokens() -> None:
    delete_json(TOKEN_FILE)


# --- Board-Auswahl ------------------------------------------------------------

SELECTION_FILE = "selected_boards.json"


def load_selected_boards() -> list[str]:
    return read_json(SELECTION_FILE, default=[])


def save_selected_boards(board_ids: list[str]) -> None:
    write_json(SELECTION_FILE, board_ids)


# --- Pins ---------------------------------------------------------------------

PINS_FILE = "pins.json"


def load_pins() -> dict:
    """Gibt {"fetched_at": ..., "pins": [...]} zurück (leer, wenn noch nichts geladen)."""
    return read_json(PINS_FILE, default={"fetched_at": None, "pins": []})


# Zwischengespeicherte Online-Suchen (siehe products.CachedSource)
SEARCH_CACHES = ["ebay_cache.json", "etsy_cache.json"]


def save_pins(data: dict) -> None:
    write_json(PINS_FILE, data)
    # Neue Pins = neues Stilprofil -> zwischengespeicherte Suchen verwerfen
    for cache in SEARCH_CACHES:
        delete_json(cache)
