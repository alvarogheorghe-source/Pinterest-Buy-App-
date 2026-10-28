"""Tägliche Sicherung (backend/backup.py)."""

import sqlite3

from backend import backup, storage


def test_backup_copies_database_and_keeps_two_weeks(fake, tmp_path):
    storage.save_pins({"pins": [{"id": "1"}]})
    target = tmp_path / "backups"
    for day in range(1, 20):
        (target / f"2026-01-{day:02d}").mkdir(parents=True)

    folder = backup.run(target)

    rows = sqlite3.connect(folder / storage.DB_FILE).execute("SELECT name FROM data").fetchall()
    assert ("pins.json",) in rows
    days = sorted(p.name for p in target.iterdir())
    assert len(days) == backup.KEEP_DAYS and days[-1] == folder.name
