"""Tests für die Vorstellungsseite malipin.com (scripts/build_site.py)."""

import json

import pytest

from scripts import build_site


@pytest.fixture
def site(tmp_path, monkeypatch):
    """Baut die Seite in einen Temp-Ordner – mit einem Test-Impressum (keine echten Daten)."""
    impressum = tmp_path / "impressum.json"
    impressum.write_text(json.dumps({"name": "Test Person", "adresse": "Teststraße 1, 1010 Wien",
                                     "email": "test@example.com"}))
    monkeypatch.setattr(build_site, "IMPRESSUM", impressum)
    monkeypatch.setattr(build_site, "OUT", tmp_path / "site")
    build_site.build()
    return tmp_path / "site"


def test_homepage_has_no_server_links(site):
    page = (site / "index.html").read_text()
    assert "Bald verfügbar" in page
    for server_only in ('href="/konto.html"', 'href="/shop.html', 'href="/merkliste.html"',
                        'src="/nav.js"'):
        assert server_only not in page
    assert "<body data-static" in page
    assert 'href="/impressum.html"' in page and 'href="/datenschutz.html"' in page


def test_legal_pages(site):
    impressum = (site / "impressum.html").read_text()
    assert "Test Person" in impressum and "Teststraße 1<br>1010 Wien" in impressum
    privacy = (site / "datenschutz.html").read_text()
    assert "<h1>Privacy Policy</h1>" in privacy and "Prototype" not in privacy
    assert "<strong>read-only</strong>" in privacy and "<li>" in privacy
    assert '<a href="https://www.dsb.gv.at">' in privacy
    for name in ("style.css", "bunny.js", "img/favicon.svg", "404.html"):
        assert (site / name).exists()


def test_never_published_without_impressum(tmp_path, monkeypatch):
    monkeypatch.setattr(build_site, "OUT", tmp_path / "site")
    monkeypatch.setattr(build_site, "IMPRESSUM", tmp_path / "fehlt.json")
    with pytest.raises(build_site.BuildError, match="fehlt"):
        build_site.build()
    empty = tmp_path / "leer.json"
    empty.write_text(json.dumps({"name": "Test", "adresse": "", "email": ""}))
    monkeypatch.setattr(build_site, "IMPRESSUM", empty)
    with pytest.raises(build_site.BuildError, match="adresse, email"):
        build_site.build()


def test_impressum_is_escaped(tmp_path, monkeypatch):
    impressum = tmp_path / "impressum.json"
    impressum.write_text(json.dumps({"name": "<script>x</script>", "adresse": "A, B",
                                     "email": "a@b.c"}))
    monkeypatch.setattr(build_site, "IMPRESSUM", impressum)
    assert "<script>x" not in build_site.impressum_page()
