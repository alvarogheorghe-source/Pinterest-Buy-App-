"""SEO: Meta-Tags, strukturierte Daten, robots.txt/sitemap, noindex für persönliche Seiten."""

import json
import re
import struct
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from scripts import build_site, seo
from tests.test_build_site import site  # noqa: F401  (Fixture)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
INDEX = (FRONTEND / "index.html").read_text("utf-8")


def tag(page, attr, name):
    match = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', page)
    return match.group(1) if match else None


def test_title_and_description_have_good_length():
    title = re.search(r"<title>([^<]+)</title>", INDEX).group(1)
    assert 30 <= len(title) <= 60 and "Pinterest" in title
    assert 120 <= len(tag(INDEX, "name", "description")) <= 160
    assert INDEX.count("<h1") == 1
    assert '<link rel="canonical" href="https://malipin.com/">' in INDEX


def test_share_preview_tags_and_images():
    for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
        assert tag(INDEX, "property", prop), prop
    assert tag(INDEX, "name", "twitter:card") == "summary_large_image"
    width, height = struct.unpack(">II", (FRONTEND / "img/og-image.png").read_bytes()[16:24])
    assert (width, height) == (1200, 630)
    for icon in json.loads((FRONTEND / "site.webmanifest").read_text())["icons"]:
        assert (FRONTEND / icon["src"].lstrip("/")).exists()


def test_structured_data_is_valid_and_up_to_date():
    """FAQ-Daten = sichtbare Fragen. Schlägt fehl? -> python -m scripts.seo ausführen."""
    assert seo.render(INDEX) == INDEX, "JSON-LD veraltet – bitte: python -m scripts.seo"
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', INDEX, re.DOTALL)
    data = json.loads(block.group(1))
    types = [item["@type"] for item in data["@graph"]]
    assert types == ["Organization", "WebSite", "WebApplication", "FAQPage"]
    questions = data["@graph"][3]["mainEntity"]
    assert len(questions) == INDEX.count("<summary>") >= 5
    assert all(q["name"] and q["acceptedAnswer"]["text"] for q in questions)


def test_personal_app_pages_are_not_indexed():
    for name in ("konto", "merkliste", "shop", "produkt", "admin"):
        page = (FRONTEND / f"{name}.html").read_text("utf-8")
        assert "noindex" in (tag(page, "name", "robots") or ""), name
    client = TestClient(app)
    robots = client.get("/robots.txt").text
    assert "Disallow: /api/" in robots and "Sitemap:" in robots
    assert client.get("/site.webmanifest").status_code == 200


def test_public_site_has_robots_sitemap_and_subpage_meta(site):  # noqa: F811
    assert "Sitemap: https://malipin.com/sitemap.xml" in (site / "robots.txt").read_text()
    sitemap = (site / "sitemap.xml").read_text()
    assert sitemap.count("<loc>") == len(build_site.PAGES) and "404" not in sitemap
    impressum = (site / "impressum.html").read_text()
    assert '<link rel="canonical" href="https://malipin.com/impressum.html">' in impressum
    assert 'content="noindex"' in (site / "404.html").read_text()
    assert '<html lang="en">' in (site / "datenschutz.html").read_text()
    for name in ("img/og-image.png", "img/icon-512.png", "site.webmanifest"):
        assert (site / name).exists()
    index = (site / "index.html").read_text()
    assert "application/ld+json" in index and 'src="/nav.js' not in index
