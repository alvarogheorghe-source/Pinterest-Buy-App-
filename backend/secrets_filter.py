"""Geheime Schlüssel nie in Fehlermeldungen oder Logs.

Scheitert eine Anfrage an eBay, Etsy, AliExpress oder Awin, steht in der Fehlermeldung oft die
ganze Adresse – und bei manchen Diensten steckt der Schlüssel in der Adresse (AliExpress:
?app_key=…, Awin: …/apikey/…/). Solche Meldungen landen sonst im Server-Log oder als Warnung im
Browser. redact() ersetzt jeden Schlüssel aus der .env durch ***; install() macht das für jede
Log-Zeile der App automatisch.
"""

import logging
import os
import re

# .env-Namen, deren Werte geheim sind
SECRET_NAME = re.compile(r"KEY|SECRET|TOKEN|PASSWORD", re.I)
MIN_LENGTH = 6          # kürzere Werte nicht ersetzen (sonst würde z.B. "1" überall gesternt)
# Typische Stellen, an denen Schlüssel in Adressen stehen – auch wenn sie nicht in .env sind
IN_URL = [
    re.compile(r"(/apikey/)[^/\s'\"]+", re.I),
    re.compile(r"([?&](?:app_key|api_key|apikey|key|access_token|refresh_token|token|sign|"
               r"client_secret|secret)=)[^&\s'\"]+", re.I),
    re.compile(r"((?:Bearer|Basic)\s+)[A-Za-z0-9._~+/=-]{8,}"),
]


def secret_values() -> list[str]:
    values = {value.strip() for name, value in os.environ.items()
              if SECRET_NAME.search(name) and len(value.strip()) >= MIN_LENGTH}
    return sorted(values, key=len, reverse=True)      # längere zuerst (falls einer im anderen steckt)


def redact(text: str) -> str:
    """Text ohne geheime Schlüssel (für Fehlermeldungen und Logs)."""
    text = str(text)
    for value in secret_values():
        text = text.replace(value, "***")
    for pattern in IN_URL:
        text = pattern.sub(r"\1***", text)
    return text


_installed = {"done": False}


def install() -> None:
    """Jede Log-Zeile (auch Fehler-Tracebacks) wird beim Entstehen bereinigt."""
    if _installed["done"]:
        return
    _installed["done"] = True
    original = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = original(*args, **kwargs)
        try:
            # Platzhalter und Argumente einzeln bereinigen: Die Form von args muss bleiben,
            # weil z. B. der Zugriffslog von uvicorn genau 5 Werte erwartet.
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            if record.exc_info:
                record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        except Exception:  # noqa: BLE001  (Logging darf nie selbst abstürzen)
            pass
        return record

    logging.setLogRecordFactory(factory)
