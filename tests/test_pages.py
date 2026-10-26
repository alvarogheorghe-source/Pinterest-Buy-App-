"""Tests: Sind alle Seiten des Frontends erreichbar?

Starten mit:  pytest -v
"""

import re

import pytest


def test_start_page_presents_the_app(fake, client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Kostenlos starten" in response.text
    assert 'href="/konto.html"' in response.text  # führt zum Konto (Pinterest verbinden)


@pytest.mark.parametrize("path", ["/shop.html", "/konto.html", "/style.css",
                                  "/landing.css", "/shop.js", "/konto.js"])
def test_pages_and_files_exist(client, path):
    assert client.get(path).status_code == 200


def test_many_connect_buttons_all_lead_to_konto(fake, client):
    """Die Startseite lädt an mehreren Stellen zum Verbinden ein – alle führen zu /konto.html."""
    import re
    html = client.get("/").text
    buttons = re.findall(r'<a href="([^"]+)" class="button[^"]*connect[^"]*">', html)
    assert len(buttons) >= 3
    assert set(buttons) == {"/konto.html"}


@pytest.mark.parametrize("path", ["/", "/shop.html", "/konto.html", "/produkt.html", "/foto.html",
                                  "/merkliste.html"])
def test_every_page_loads_mali(fake, client, path):
    html = client.get(path).text
    assert re.search(r'<script src="bunny.js"( defer)?></script>', html)
    assert 'href="bunny.css"' in html


# --- Verbunden -> direkt in den Shop -------------------------------------------------------

def test_connected_users_skip_the_start_page(fake, client):
    from tests.conftest import save_tokens
    save_tokens()  # so tun, als wäre Pinterest verbunden
    response = client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/shop.html"
    # Die Startseite selbst bleibt erreichbar
    assert "Kostenlos starten" in client.get("/index.html").text


def test_logout_brings_the_start_page_back(fake, client):
    from tests.conftest import save_tokens
    save_tokens()
    client.post("/auth/logout")
    response = client.get("/")
    assert response.status_code == 200 and "Kostenlos starten" in response.text


@pytest.mark.parametrize("path", ["/", "/shop.html", "/konto.html", "/produkt.html", "/merkliste.html", "/foto.html"])
def test_every_page_has_the_mali_logo(client, path):
    """Logo (Mali als Pinnadel) und Tab-Symbol – erzeugt von scripts/make_logo.py."""
    html = client.get(path).text
    assert 'class="logo-pin"' in html and 'href="/img/favicon.svg"' in html
    assert client.get("/img/favicon.svg").headers["content-type"].startswith("image/svg+xml")


def test_frontend_files_are_revalidated(client):
    assert client.get("/style.css").headers["cache-control"] == "no-cache"
