"""Tägliche Sicherung: Datenbank + Einstellungen in backups/JJJJ-MM-TT/, die letzten 14 Tage bleiben.

Auf dem Server läuft das jede Nacht (deploy/malipin-nightly.service). Von Hand:
    python -m backend.backup
Zurückspielen: Dienst stoppen, Dateien aus dem Ordner nach data/ kopieren, Dienst starten
(docs/SERVER.md).
"""

import shutil
import sqlite3
import time
from pathlib import Path

from backend import storage
from backend.config import BASE_DIR

BACKUP_DIR = BASE_DIR / "backups"
KEEP_DAYS = 14


def run(target: Path | None = None, keep: int = KEEP_DAYS) -> Path:
    target = target or BACKUP_DIR
    folder = target / time.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)

    database = storage.DATA_DIR / storage.DB_FILE
    if database.exists():
        # SQLite-eigene Sicherung: klappt auch, während die App gerade schreibt
        source, copy = sqlite3.connect(database), sqlite3.connect(folder / storage.DB_FILE)
        with copy:
            source.backup(copy)
        source.close()
        copy.close()
    # Neben der Datenbank: Einstellungen, die man nicht neu herunterladen kann
    for path in (BASE_DIR / "feeds.json", storage.DATA_DIR / "trusted_shops.json"):
        if path.exists():
            shutil.copy2(path, folder / path.name)

    # Alte Sicherungen löschen (Ordnernamen sind Daten, also nach Name sortierbar)
    days = sorted(p for p in target.iterdir() if p.is_dir())
    for old in days[:-keep]:
        shutil.rmtree(old)
    return folder


if __name__ == "__main__":
    print(f"Gesichert nach {run()}")
