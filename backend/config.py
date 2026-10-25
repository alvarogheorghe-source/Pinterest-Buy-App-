"""Zentrale Einstellungen der App.

Alle geheimen Werte kommen aus der Datei .env (bzw. aus Umgebungsvariablen),
niemals direkt aus dem Code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Projektordner = eine Ebene über backend/
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# .env einlesen (falls vorhanden). Die Werte landen in os.environ.
load_dotenv(BASE_DIR / ".env")


class ConfigError(Exception):
    """Wird geworfen, wenn ein nötiger Wert in .env fehlt."""


def get_setting(name: str) -> str:
    """Liest eine Einstellung und meldet verständlich, wenn sie fehlt.

    Wir lesen erst beim Gebrauch (nicht beim Start), damit der Server
    auch ohne .env startet – z.B. für /health.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"'{name}' fehlt. Kopiere .env.example zu .env und trage den Wert ein."
        )
    return value
