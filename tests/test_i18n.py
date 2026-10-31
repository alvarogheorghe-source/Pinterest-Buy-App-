"""Zweisprachige Website (scripts/i18n.py + build_site): / = Deutsch, /en/ = Englisch."""

import pytest

from scripts import build_site, i18n
from tests.test_build_site import site  # noqa: F401  (Fixture)


def test_translate_texts_attributes_and_text_after_icons():
    page = ('<html><head><meta name="description" content="Hallo Welt"><title>Titel</title></head>'
            '<p><svg><title>Titel</title></svg>Nur Lesezugriff</p><img alt="Bild &amp; Text">'
            '<script>const x = "Titel";</script><!-- Titel --></html>')
    out = i18n.translate(page, {"Hallo Welt": "Hello world", "Titel": "Title",
                                "Nur Lesezugriff": "Read-only access", "Bild & Text": "Image & text"})
    assert 'content="Hello world"' in out and "<title>Title</title>" in out
    assert "</svg>Read-only access</p>" in out and 'alt="Image &amp; text"' in out
    assert '<svg><title>Titel</title></svg>' in out                  # Grafik unangetastet
    assert 'const x = "Titel"' in out and "<!-- Titel -->" in out     # Code/Kommentar unangetastet


def test_every_homepage_text_has_an_english_translation():
    """Schlägt fehl? Neuen deutschen Text in frontend/i18n/en.json übersetzen."""
    german = build_site.static_index((build_site.FRONTEND / "index.html").read_text("utf-8"))
    translations, same = i18n.load()
    assert i18n.missing(german, translations, same) == []


def test_missing_translation_stops_the_build():
    with pytest.raises(build_site.BuildError, match="Übersetzung fehlt"):
        build_site.english_index("<html lang=\"de\"><p>Ganz neuer Satz</p></html>")


def test_english_page(site):  # noqa: F811
    en = (site / "en" / "index.html").read_text()
    assert '<html lang="en">' in en and "Saw an outfit?" in en and "Outfit gesehen?" not in en
    assert '<link rel="canonical" href="https://malipin.com/en/">' in en
    assert 'hreflang="de" href="https://malipin.com/"' in en
    assert "/img/og-image-en.png" in en and '"inLanguage": "en"' in en
    assert 'href="/" class="header-link lang-switch"' in en           # zurück zu Deutsch
    de = (site / "index.html").read_text()
    assert 'href="/en/" class="header-link lang-switch"' in de and 'id="lang-hint"' in de
    assert 'hreflang="x-default"' in de
    sitemap = (site / "sitemap.xml").read_text()
    assert "<loc>https://malipin.com/en/</loc>" in sitemap and 'hreflang="en"' in sitemap
