"""Liest einen Preis aus einem Text, z.B. aus der Beschreibung eines Depop-Pins.

Es zählen nur Zahlen MIT Währung ("25€", "£18", "EUR 25"), damit z.B.
"Größe 38" oder "90s" nicht als Preis erkannt werden.
"""

import re

# Währungszeichen/-wörter -> Währungscode
CURRENCIES = {
    "€": "EUR", "eur": "EUR", "euro": "EUR",
    "£": "GBP", "gbp": "GBP",
    "$": "USD", "usd": "USD",
    "chf": "CHF",
}

# Zahl: 25 | 25,50 | 25.50 | 1.299 | 1.299,00
# (Leerzeichen als Tausendertrenner bewusst NICHT, sonst wird "Größe 38 250€" zu 38250)
AMOUNT = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
# Wörter brauchen Wortgrenzen (sonst passt "eur" in "Europa"), Zeichen nicht
CURRENCY = r"€|£|\$|\b(?:euro|eur|gbp|usd|chf)\b"

# Währung vor ODER nach der Zahl, mit oder ohne Leerzeichen
PRICE_PATTERN = re.compile(
    rf"(?P<cur1>{CURRENCY})\s?(?P<amount1>{AMOUNT})"
    rf"|(?P<amount2>{AMOUNT})\s?(?P<cur2>{CURRENCY})",
    re.IGNORECASE,
)


def parse_amount(text: str) -> float:
    """Wandelt "1.299,00" oder "25.50" in eine Zahl um."""
    if "," in text and "." in text:
        # Das HINTERE Zeichen ist das Dezimaltrennzeichen: 1.299,00 oder 1,299.00
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        # 25,50 -> Dezimal; 1,299 -> Tausender
        whole, _, rest = text.rpartition(",")
        text = f"{whole}.{rest}" if len(rest) <= 2 else whole + rest
    elif "." in text:
        # 25.50 -> Dezimal; 1.299 -> Tausender
        whole, _, rest = text.rpartition(".")
        text = f"{whole}.{rest}" if len(rest) <= 2 else whole + rest
    return float(text)


def extract_price(text: str | None) -> dict | None:
    """Gibt den ERSTEN Preis im Text zurück, z.B. {"price": 25.0, "currency": "EUR"}."""
    if not text:
        return None
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    amount = match.group("amount1") or match.group("amount2")
    currency = (match.group("cur1") or match.group("cur2")).lower()
    return {"price": parse_amount(amount), "currency": CURRENCIES[currency]}
