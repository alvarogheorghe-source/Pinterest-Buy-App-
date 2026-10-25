"""Tests für Teil A, Schritt 2: Preise aus Pin-Texten lesen.

Starten mit:  pytest -v
"""

import pytest

from backend.prices import extract_price


@pytest.mark.parametrize("text, price, currency", [
    ("Beige Hoodie 25€", 25.0, "EUR"),
    ("Beige Hoodie 25 €", 25.0, "EUR"),
    ("nur €25!", 25.0, "EUR"),
    ("Preis: € 25,50", 25.5, "EUR"),
    ("25.50€ inkl. Versand", 25.5, "EUR"),
    ("EUR 18", 18.0, "EUR"),
    ("18 Euro VB", 18.0, "EUR"),
    ("Mantel 1.299,00 €", 1299.0, "EUR"),
    ("Mantel 1.299 €", 1299.0, "EUR"),
    ("vintage jacket £18", 18.0, "GBP"),
    ("cargo pants $30.99", 30.99, "USD"),
    ("CHF 40", 40.0, "CHF"),
    ("Größe 38, NP 60€, jetzt 25€", 60.0, "EUR"),  # bewusst: der ERSTE Preis zählt
    ("Größe 38 25€", 25.0, "EUR"),                  # Größe davor stört nicht
    ("Größe 38 250€", 250.0, "EUR"),                # ... auch nicht bei 3 Stellen
    ("coat 1,299.00 €", 1299.0, "EUR"),             # englische Schreibweise
])
def test_prices_are_found(text, price, currency):
    assert extract_price(text) == {"price": price, "currency": currency}


@pytest.mark.parametrize("text", [
    None,
    "",
    "Oversized Hoodie Größe 38",
    "90s vintage denim",
    "100% Baumwolle",
    "Europa Tour Shirt 2024",   # "Eur" in "Europa" ist keine Währung
])
def test_no_price(text):
    assert extract_price(text) is None
