"""Tests: Sind alle Seiten des Frontends erreichbar?

Starten mit:  pytest -v
"""

import pytest


def test_start_page_presents_the_app(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Kostenlos starten" in response.text
    assert 'href="/konto.html"' in response.text  # führt zum Konto (Pinterest verbinden)


@pytest.mark.parametrize("path", ["/shop.html", "/konto.html", "/style.css",
                                  "/landing.css", "/shop.js", "/konto.js"])
def test_pages_and_files_exist(client, path):
    assert client.get(path).status_code == 200


def test_many_connect_buttons_all_lead_to_konto(client):
    """Die Startseite lädt an mehreren Stellen zum Verbinden ein – alle führen zu /konto.html."""
    import re
    html = client.get("/").text
    buttons = re.findall(r'<a href="([^"]+)" class="button[^"]*connect[^"]*">', html)
    assert len(buttons) >= 6
    assert set(buttons) == {"/konto.html"}
