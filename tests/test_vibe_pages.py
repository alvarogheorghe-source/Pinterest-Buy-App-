"""Eine Seite pro Vibe (backend/vibe_pages.py) + Sitemap."""

from backend import vibe_pages


def test_vibe_page_has_own_title_text_and_links(fake, client):
    response = client.get("/stil/goth-baddie", headers={"Accept-Language": "de"})
    assert response.status_code == 200
    html = response.text
    assert "<title>Goth Baddie Vibe, Bedeutung und typische Teile | Malipin</title>" in html
    assert '<link rel="canonical" href="https://malipin.com/stil/goth-baddie">' in html
    assert "<h1" in html and "Plateau-Boots" in html                   # typische Teile
    assert 'href="/foto.html"' in html and 'href="/stil/clean-girl"' in html
    assert "/impressum.html" in html and "stile.js" not in html
    assert html.count('name="description"') == 1


def test_vibe_page_in_english(fake, client):
    html = client.get("/stil/goth-baddie", cookies={"lang": "en"}).text
    assert '<html lang="en">' in html and "Platform boots" in html


def test_unknown_vibe_is_404(fake, client):
    assert client.get("/stil/gibts-nicht").status_code == 404


def test_sitemap_lists_every_vibe(fake, client):
    xml = client.get("/sitemap.xml").text
    for path in vibe_pages.all_paths():
        assert f"<loc>https://malipin.com{path}</loc>" in xml
    assert "<loc>https://malipin.com/stile.html</loc>" in xml
