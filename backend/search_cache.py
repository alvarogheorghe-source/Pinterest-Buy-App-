"""Gemeinsamer Zwischenspeicher für Shop-Suchen (eBay & Co.) – für ALLE Personen.

Suchen zwei Personen "Baggy Light Wash Jeans" auf ebay.at, fragt Malipin eBay nur einmal pro
Stunde. So können wir pro Person viel mehr suchen (mehr Angebote), ohne eBays Tageslimit
(5.000 Anfragen) zu sprengen.

Eigene kleine SQLite-Datei (data/search_cache.db): schnell, sicher bei gleichzeitigen
Zugriffen, alte Einträge werden aufgeräumt. Gespeichert werden nur öffentliche Angebote –
keine Daten über Personen.
"""

import json
import sqlite3
import time

from backend import storage

DB_FILE = "search_cache.db"
MAX_AGE = 60 * 60            # 1 Stunde – Preise und Verfügbarkeit ändern sich
MAX_ENTRIES = 5000           # danach fliegen die ältesten raus


def _connect() -> sqlite3.Connection:
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(storage.DATA_DIR / DB_FILE, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS searches "
                       "(key TEXT PRIMARY KEY, fetched_at REAL, items TEXT)")
    return connection


def get(key: str, max_age: float = MAX_AGE) -> list[dict] | None:
    with _connect() as db:
        row = db.execute("SELECT fetched_at, items FROM searches WHERE key = ?", (key,)).fetchone()
    if row and row[0] > time.time() - max_age:
        return json.loads(row[1])
    return None


def put(key: str, items: list[dict]) -> None:
    with _connect() as db:
        db.execute("INSERT OR REPLACE INTO searches VALUES (?, ?, ?)",
                   (key, time.time(), json.dumps(items, ensure_ascii=False)))
        count = db.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
        if count > MAX_ENTRIES:
            db.execute("DELETE FROM searches WHERE key IN (SELECT key FROM searches "
                       "ORDER BY fetched_at LIMIT ?)", (count - MAX_ENTRIES,))


def cached(key: str, fetch) -> list[dict]:
    """Treffer aus dem Speicher – sonst fetch() aufrufen und merken."""
    items = get(key)
    if items is None:
        items = fetch()
        put(key, items)
    return items
