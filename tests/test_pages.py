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


def test_landing_leads_with_photo_search(fake, client):
    """Solange Pinterest zu ist: die Startseite führt zur Foto-Suche, ohne tote Pinterest-Knöpfe,
    und zeigt echte Outfits aus dem Katalog (vom Server eingesetzt)."""
    import re
    html = client.get("/").text
    hero = html.split('<section class="hero">')[1].split("</section>")[0]
    assert re.search(r'<a href="/foto.html" class="button large">', hero)
    assert "connect" not in html.split('<main id="main">')[1].split("</main>")[0]
    assert 'class="hero-outfit' in hero and "HERO_OUTFIT" not in html and "OUTFIT_IDEAS" not in html
    assert client.get("/index.html").text == html


@pytest.mark.parametrize("path", ["/", "/shop.html", "/konto.html", "/produkt.html", "/foto.html",
                                  "/merkliste.html"])
def test_every_page_loads_mali(fake, client, path):
    html = client.get(path).text
    assert re.search(r'<script src="/bunny.js"( defer)?></script>', html)
    assert 'href="/bunny.css"' in html


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


def test_every_page_links_privacy_and_imprint():
    """Impressum und Datenschutz müssen von jeder Seite aus erreichbar sein."""
    from backend.config import FRONTEND_DIR
    for page in FRONTEND_DIR.glob("*.html"):
        if page.name == "admin.html":
            continue
        html = page.read_text(encoding="utf-8")
        assert "/impressum.html" in html and "/datenschutz.html" in html, page.name
        assert "/nutzungsbedingungen.html" in html, page.name


def test_every_public_page_has_amazon_disclosure():
    """Pflicht im Amazon-Partnerprogramm: der Hinweis muss auf der Seite stehen."""
    from backend.config import FRONTEND_DIR
    for page in FRONTEND_DIR.glob("*.html"):
        if page.name != "admin.html":
            assert "Als Amazon-Partner verdienen wir an qualifizierten Verkäufen." in page.read_text("utf-8"), page.name


def test_unknown_page_shows_friendly_404(client):
    response = client.get("/gibtsnicht.html", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "Hoppla" in response.text and 'href="/foto.html"' in response.text
    assert 'name="robots" content="noindex"' in response.text
    api = client.get("/api/gibtsnicht", headers={"Accept": "text/html"})
    assert api.status_code == 404 and api.json()["detail"]


def test_api_docs_only_locally():
    """Auf dem Server (PUBLIC_URL gesetzt) keine /docs und /openapi.json für Besucher."""
    import subprocess
    import sys
    code = ("from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); "
            "print(c.get('/docs').status_code, c.get('/openapi.json').status_code)")
    run = lambda env: subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,  # noqa: E731
                                     env={**__import__("os").environ, **env}).stdout.split()[-2:]
    assert run({"PUBLIC_URL": "https://malipin.com"}) == ["404", "404"]
    assert run({"PUBLIC_URL": ""}) == ["200", "200"]


def test_images_are_cached_pages_are_not(client):
    assert client.get("/img/favicon.svg").headers["cache-control"] == "public, max-age=604800"
    assert client.get("/style.css").headers["cache-control"] == "no-cache"


def test_terms_page(client):
    html = client.get("/nutzungsbedingungen.html").text
    assert "<h1>Nutzungsbedingungen</h1>" in html and "verkauft selbst nichts" in html
    assert '<a href="/impressum.html">Impressum</a>' in html             # Links im Text
    assert client.get("/terms.html").text == html
    assert "/nutzungsbedingungen.html" in client.get("/sitemap.xml").text
