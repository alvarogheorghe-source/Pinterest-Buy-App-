"""Währungen umrechnen – Kurse der Europäischen Zentralbank (kostenlos, täglich neu).

Die Kurse (Basis Euro) liegen in data/exchange_rates.json, für alle gleich, und werden
einmal am Tag im Hintergrund erneuert. Klappt das nicht (offline, EZB nicht erreichbar),
gelten die letzten gespeicherten Kurse – und ganz am Anfang ungefähre Ersatzkurse.

    convert(20, "EUR", "USD")  -> 21.6   (None, wenn eine Währung unbekannt ist)
"""

import logging
import threading
import time
import xml.etree.ElementTree as ET

import httpx

from backend import storage

logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
RATES_FILE = "exchange_rates.json"         # für alle gleich (storage.GLOBAL_FILES)
MAX_AGE = 24 * 60 * 60
# Ungefähre Kurse (1 € = …) – nur bis die echten Kurse einmal geladen sind
FALLBACK = {"EUR": 1.0, "USD": 1.08, "GBP": 0.85, "CHF": 0.95, "CAD": 1.48, "AUD": 1.65,
            "SEK": 11.4, "DKK": 7.46, "NOK": 11.6, "PLN": 4.3, "CZK": 25.0, "JPY": 165.0}

_lock = threading.Lock()


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests die EZB simulieren können."""
    return httpx.Client(timeout=10)


def fetch_ecb() -> dict[str, float]:
    with _http() as client:
        response = client.get(ECB_URL)
    response.raise_for_status()
    rates = {"EUR": 1.0}
    for element in ET.fromstring(response.content).iter():
        if element.get("currency") and element.get("rate"):
            rates[element.get("currency")] = float(element.get("rate"))
    if len(rates) < 5:
        raise ValueError("EZB-Antwort ohne Kurse")
    return rates


def refresh() -> dict[str, float]:
    rates = fetch_ecb()
    storage.write_json(RATES_FILE, {"fetched_at": time.time(), "rates": rates})
    return rates


def _refresh_in_background() -> None:
    if not _lock.acquire(blocking=False):
        return

    def run():
        try:
            refresh()
        except Exception as err:          # offline o.ä.: alte Kurse gelten weiter
            logger.warning("Wechselkurse nicht aktualisiert: %s", err)
            # nicht bei jeder Anfrage neu versuchen – erst wieder in einer Stunde
            old = storage.read_json(RATES_FILE, default=None) or {"rates": FALLBACK}
            storage.write_json(RATES_FILE, {**old, "fetched_at": time.time() - MAX_AGE + 3600})
        finally:
            _lock.release()
    threading.Thread(target=run, daemon=True).start()


def rates() -> dict[str, float]:
    saved = storage.read_json(RATES_FILE, default=None)
    if not saved or saved.get("fetched_at", 0) < time.time() - MAX_AGE:
        _refresh_in_background()
    return {**FALLBACK, **((saved or {}).get("rates") or {})}


def convert(amount: float, source: str, target: str, table: dict | None = None) -> float | None:
    if source == target:
        return amount
    table = table or rates()
    if source not in table or target not in table:
        return None
    return round(amount / table[source] * table[target], 2)
