"""Foto hochladen → Mali findet's (backend/photo.py) – mit simuliertem KI-Modell.

Das "Foto" zeigt eine schwarze Carhartt-Jacke, Herren, Streetwear.
"""

from io import BytesIO

import httpx
import pytest
from PIL import Image

from backend import ebay, rate_limit, storage, vision
from tests.test_ebay import FakeEbay, item
from tests.test_image_tags import FakeTextEmbedder, axis

PHOTO_VECTOR = axis(("gate:person", 1.0), ("style:streetwear", 1.0), ("category:Jacken", 1.0),
                    ("brand:Carhartt", 1.0), ("gender:herren", 1.0))


def jpeg(color="#141414"):
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, "JPEG")
    return buffer.getvalue()


class PhotoEmbedder(FakeTextEmbedder):
    """Foto -> Carhartt-Jacke. Produktbilder: nur die Bomberjacke sieht genauso aus."""

    def embed_image_bytes(self, images):
        return [PHOTO_VECTOR for _ in images]

    def embed_image_urls(self, urls):
        return [PHOTO_VECTOR if "prod-006" in url or "/itm-match" in url
                else axis(("category:Hosen", 1.0)) for url in urls]


@pytest.fixture
def model(monkeypatch):
    monkeypatch.setattr(vision, "get_embedder", PhotoEmbedder)


def upload(client, data, content_type="image/jpeg"):
    return client.post("/api/photo", content=data, headers={"Content-Type": content_type})


def test_photo_finds_what_is_on_it(fake, client, model):
    result = upload(client, jpeg()).json()
    assert result["found"] == {"categories": ["Jacken"], "styles": ["streetwear"],
                               "brands": ["Carhartt"], "details": [], "colors": ["schwarz"], "gender": "herren",
                               "department": "mode"}
    products = result["products"]
    assert products[0]["id"] == "prod-006"                  # sieht genauso aus + Jacke + schwarz
    assert products[0]["looks_like_photo"] is True
    assert all(p["department"] == "mode" for p in products)  # keine Vasen zur Jacke
    assert [p["id"] for p in products] == ["prod-006"]      # nur was dem Foto wirklich ähnlich sieht


def test_photo_is_never_stored(fake, client, model):
    upload(client, jpeg())
    stored = [f.name for f in storage.DATA_DIR.iterdir()]
    assert not any(name.endswith((".jpg", ".jpeg", ".png")) for name in stored)
    assert "photo_results.json" not in stored               # Demo-Katalog: nichts zu merken


def test_bad_uploads(fake, client, model):
    assert upload(client, b"kein bild").status_code == 400
    assert upload(client, b"", "image/png").status_code == 400
    assert upload(client, jpeg(), "text/plain").status_code == 415


def test_without_ai_packages(fake, client, monkeypatch):
    def unavailable():
        raise vision.VisionUnavailable("fehlt")
    monkeypatch.setattr(vision, "get_embedder", unavailable)
    response = upload(client, jpeg())
    assert response.status_code == 503 and "requirements-ai" in response.json()["detail"]


def test_online_search_only_for_what_is_on_the_photo(fake, client, model, monkeypatch):
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    monkeypatch.setenv("EBAY_CLIENT_ID", "id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    monkeypatch.delenv("ETSY_API_KEY", raising=False)
    ebay._token.clear()
    fake_ebay = FakeEbay()
    fake_ebay.results["Herren Carhartt Jacke"] = [
        {**item("match", "Carhartt Detroit Jacket Schwarz Herren"),
         "image": {"imageUrl": "https://i.ebayimg.com/itm-match.jpg"}},
        item("other", "Carhartt Jacke Braun"),
    ]
    transport = httpx.MockTransport(fake_ebay.handler)
    monkeypatch.setattr(ebay, "_http", lambda: httpx.Client(transport=transport))

    products = upload(client, jpeg()).json()["products"]
    assert [p["id"] for p in products] == ["ebay-match"]     # die braune Jacke sieht anders aus
    assert [p["id"] for p in client.get("/api/recommendations").json()["products"]] == ["ebay-match"]
    assert all("Jacke" in q for q in fake_ebay.searches())   # keine Suche nach Hosen, Schuhen …
    # Gemerkt -> ♡ und Detailseite funktionieren auch für Foto-Ergebnisse
    assert client.post("/api/feedback", json={"product_id": "ebay-match", "vote": "like"}).status_code == 200
    assert client.get("/api/products/ebay-match").status_code == 200


def test_desktop_screenshot_finds_nothing(fake, client, monkeypatch):
    class DesktopEmbedder(PhotoEmbedder):
        def embed_image_bytes(self, images):
            return [axis(("gate:desktop", 1.0), ("style:minimalistisch", 1.0),
                         ("category:Wandgestaltung", 1.0)) for _ in images]
    monkeypatch.setattr(vision, "get_embedder", DesktopEmbedder)
    result = upload(client, jpeg("#3a6ea5")).json()
    assert result == {"relevant": False, "seen": "desktop", "found": None, "products": []}


def test_force_searches_anyway(fake, client, monkeypatch):
    class DesktopEmbedder(PhotoEmbedder):
        def embed_image_bytes(self, images):
            return [axis(("gate:desktop", 1.0)) for _ in images]
    monkeypatch.setattr(vision, "get_embedder", DesktopEmbedder)
    response = client.post("/api/photo?force=true", content=jpeg("#3a6ea5"),
                           headers={"Content-Type": "image/jpeg"})
    assert response.json()["relevant"] is True


def test_too_many_photos_are_slowed_down(fake, client, model):
    for _ in range(rate_limit.LIMIT):
        assert upload(client, jpeg()).status_code == 200
    response = upload(client, jpeg())
    assert response.status_code == 429 and "Minuten" in response.json()["detail"]


def test_photo_compares_all_precomputed_images(fake, client, model, monkeypatch):
    """Ein Foto hat keinen Text: auch Produkte jenseits der Text-Besten zählen, wenn ihr Bild
    schon berechnet ist (nächtliche Bilderkennung)."""
    from backend import photo
    monkeypatch.setattr(photo, "VISUAL_CHECK", 0)            # kein Text-Treffer wird nachgeladen
    store = vision.EmbeddingStore(PhotoEmbedder.name)
    store.put("product:prod-006", "/img/products/prod-006.png", PHOTO_VECTOR)
    store.save()
    products = upload(client, jpeg()).json()["products"]
    assert [p["id"] for p in products] == ["prod-006"]
