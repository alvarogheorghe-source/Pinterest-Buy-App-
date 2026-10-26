"""Datenspeicherung – getrennt pro Person.

Alles, was einer Person gehört (Pinterest-Zugang, Pins, Merkliste, Analyse-Stand, Such-
Zwischenspeicher …), liegt in einer kleinen SQLite-Datenbank (data/malipin.db): eine Zeile pro
Person und "Datei". Die übrige App merkt davon nichts – sie ruft weiter read_json("pins.json")
usw. auf und bekommt automatisch die Daten der aktuellen Person (current_user()).

Wer die aktuelle Person ist, setzt main.py pro Anfrage (anonyme Kennung im Cookie). Ohne
MULTI_USER=1 in .env ist es immer "local" – lokal und für die Befehle im Terminal ändert
sich also nichts.

Gemeinsam für alle (echte Dateien in data/): GLOBAL_FILES, z.B. die Bild-Fingerabdrücke –
ein Bild sieht für alle gleich aus.
"""

import contextvars
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from backend.config import BASE_DIR

# Als Variable, damit Tests einen Temp-Ordner unterschieben können
DATA_DIR = BASE_DIR / "data"
DB_FILE = "malipin.db"
LOCAL_USER = "local"

# Für alle gemeinsam (keine persönlichen Daten)
GLOBAL_FILES = {"embeddings.json", "trusted_shops.json"}   # geprüfte Shops: für alle gleich

# Frühere Einzel-Dateien, die beim ersten Start in die Datenbank (Person "local") wandern
LEGACY_FILES = ["tokens.json", "selected_boards.json", "pins.json", "feedback.json",
                "analysis.json", "ebay_cache.json", "etsy_cache.json", "photo_results.json",
                "aliexpress_cache.json"]
LEGACY_FOLDER = "alt-vor-datenbank"

_current_user: contextvars.ContextVar[str] = contextvars.ContextVar("malipin_user",
                                                                     default=LOCAL_USER)


def current_user() -> str:
    return _current_user.get()


def set_user(user_id: str) -> contextvars.Token:
    """Für die Dauer einer Anfrage festlegen, wessen Daten gelesen/geschrieben werden."""
    return _current_user.set(user_id)


def reset_user(token: contextvars.Token) -> None:
    _current_user.reset(token)


# --- Datenbank ----------------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / DB_FILE
    new = not path.exists()
    db = sqlite3.connect(path, timeout=10)
    if new:
        db.execute("PRAGMA journal_mode=WAL")   # gleichzeitiges Lesen und Schreiben
        db.execute("CREATE TABLE IF NOT EXISTS data (user TEXT NOT NULL, name TEXT NOT NULL, "
                   "value TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (user, name))")
        _migrate_legacy_files(db)
        db.commit()
    return db


def _migrate_legacy_files(db: sqlite3.Connection) -> None:
    """Alte data/*.json-Dateien (vor der Datenbank) als Person "local" übernehmen und dann in
    data/alt-vor-datenbank/ verschieben – nichts geht verloren."""
    for name in LEGACY_FILES:
        old = DATA_DIR / name
        if not old.exists():
            continue
        db.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)",
                   (LOCAL_USER, name, old.read_text(encoding="utf-8"), time.time()))
        (DATA_DIR / LEGACY_FOLDER).mkdir(exist_ok=True)
        old.rename(DATA_DIR / LEGACY_FOLDER / name)


def _path(filename: str) -> Path:
    return DATA_DIR / filename


def read_json(filename: str, default=None):
    """Gemeinsame Datei oder Eintrag der aktuellen Person. `default`, wenn es ihn nicht gibt."""
    if filename in GLOBAL_FILES:
        path = _path(filename)
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    with _connect() as db:
        row = db.execute("SELECT value FROM data WHERE user = ? AND name = ?",
                         (current_user(), filename)).fetchone()
    return json.loads(row[0]) if row else default


def write_json(filename: str, data) -> None:
    if filename in GLOBAL_FILES:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _path(filename).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return
    with _connect() as db:
        db.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)",
                   (current_user(), filename, json.dumps(data, ensure_ascii=False), time.time()))


def delete_json(filename: str) -> None:
    if filename in GLOBAL_FILES:
        _path(filename).unlink(missing_ok=True)
        return
    with _connect() as db:
        db.execute("DELETE FROM data WHERE user = ? AND name = ?", (current_user(), filename))


def exists(filename: str) -> bool:
    return read_json(filename) is not None


def linked_user_id(account_id: str) -> str:
    """Feste Kennung zu einem Pinterest-Konto – gleich auf jedem Gerät. Gespeichert wird nur
    eine Prüfsumme, nicht die Pinterest-ID selbst."""
    return "p-" + hashlib.sha256(f"pinterest:{account_id}".encode()).hexdigest()[:32]


# Beim Zusammenführen: was gewinnt? Tokens -> die neuen; Merkliste -> beide zusammen;
# alles andere -> was beim Pinterest-Konto schon da ist (sonst das Neue)
_TAKE_NEW = {"tokens.json"}
_MERGE_DICTS = {"feedback.json"}


def merge_user_data(source: str, target: str) -> None:
    """Daten der anonymen Kennung `source` in `target` (Pinterest-Konto) übernehmen."""
    if source == target:
        return
    with _connect() as db:
        rows = db.execute("SELECT name, value FROM data WHERE user = ?", (source,)).fetchall()
        for name, value in rows:
            existing = db.execute("SELECT value FROM data WHERE user = ? AND name = ?",
                                  (target, name)).fetchone()
            if existing and name in _MERGE_DICTS:
                value = json.dumps({**json.loads(existing[0]), **json.loads(value)},
                                   ensure_ascii=False)
            elif existing and name not in _TAKE_NEW:
                continue
            db.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)",
                       (target, name, value, time.time()))
        db.execute("DELETE FROM data WHERE user = ?", (source,))


def delete_user_data() -> int:
    """"Alle meine Daten löschen": entfernt ALLES der aktuellen Person. Gibt die Anzahl zurück."""
    with _connect() as db:
        return db.execute("DELETE FROM data WHERE user = ?", (current_user(),)).rowcount


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
SEARCH_CACHES = ["ebay_cache.json", "etsy_cache.json", "aliexpress_cache.json"]


def save_pins(data: dict) -> None:
    write_json(PINS_FILE, data)
    # Neue Pins = neues Stilprofil -> zwischengespeicherte Suchen verwerfen
    for cache in SEARCH_CACHES:
        delete_json(cache)
