"""Produktnamen in anderen Sprachen (languages.py) werden wie Deutsch/Englisch verstanden."""

import pytest

from backend.matching import CATEGORY_PATTERNS, COLOR_PATTERNS, STYLE_PATTERNS, find_terms


@pytest.mark.parametrize("name, category, color", [
    ("Damska kurtka zimowa czarna oversize", "Jacken", "schwarz"),
    ("Spodnie damskie szerokie beżowe", "Hosen", "beige"),
    ("Sukienka midi w kwiaty różowa", "Kleider & Röcke", "rosa"),
    ("Dames spijkerbroek wijde pijp blauw", "Hosen", "blau"),
    ("Robe longue? non – Jupe plissée verte", "Kleider & Röcke", "grün"),
    ("Borsa a tracolla in pelle nera", "Accessoires", "schwarz"),
    ("Zapatillas deportivas blancas", "Schuhe", "weiß"),
    ("Wazon ceramiczny biały", "Deko", "weiß"),
    ("Poduszka dekoracyjna szara", "Textilien", "grau"),
])
def test_foreign_product_names(name, category, color):
    assert category in find_terms(name, CATEGORY_PATTERNS)
    assert color in find_terms(name, COLOR_PATTERNS)


def test_styles_and_no_false_friends():
    assert "sportlich" in find_terms("Buty sportowe męskie", STYLE_PATTERNS)
    assert "Schuhe" in find_terms("Buty sportowe męskie", CATEGORY_PATTERNS)
    # "but", "vertical", "Plaid-Muster" dürfen nichts auslösen
    assert find_terms("But wait – vertical plaid pattern", CATEGORY_PATTERNS) == set()
    assert "grün" not in find_terms("vertical stripes", COLOR_PATTERNS)
