"""Tests für die Bilderkennung (backend/vision.py) – OHNE das echte KI-Modell.

FakeEmbedder ersetzt FashionCLIP: Er macht aus der Farbe in der Bild-URL einen
Vektor (z.B. ".../d8c3a5/..." -> beige). Ähnliche Farben = ähnliche Vektoren.
Die RGB-Werte werden um die Mitte (128) verschoben, sonst zeigten Schwarz und Weiß
in dieselbe Richtung und wären "gleich".
So lassen sich Rechenwege, Speicher und Ranking prüfen, ohne 600 MB Modell.

Starten mit:  pytest -v
"""

import re

import pytest

from backend import storage, vision
from backend.evaluate import evaluate, make_visual_recommenders
from backend.products import JsonProductSource
from backend.similar import similar_products
from tests.test_products import make_product


# Eigene Produktbilder ("/img/products/prod-001.png") haben keine Farbe in der Adresse.
# Der Test-Ersatz schlägt sie deshalb über die Hauptfarbe des Produkts nach.
from scripts.make_placeholders import COLORS  # noqa: E402

PRODUCT_IMAGE_COLORS = {
    p.image_url: "{:02x}{:02x}{:02x}".format(*COLORS[p.colors[0]])
    for p in JsonProductSource().load()
}


class FakeEmbedder:
    name = "fake-model"

    def __init__(self):
        self.calls = 0

    def embed_image_urls(self, urls):
        self.calls += len(urls)
        result = []
        for url in urls:
            url = PRODUCT_IMAGE_COLORS.get(url, url)  # eigene Produktbilder -> ihre Farbe
            match = re.search(r"([0-9a-f]{6})", url or "")
            if not match or "kaputt" in url:
                result.append(None)  # Bild nicht ladbar
                continue
            hex_color = match.group(1)
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            result.append(vision.normalize([r - 128, g - 128, b - 128]))
        return result


def img(hex_color):
    return f"https://img.test/{hex_color}.jpg"


# --- Rechnen ---------------------------------------------------------------------------------

def test_normalize_and_cosine():
    v = vision.normalize([3, 4])
    assert v == [0.6, 0.8]
    assert vision.cosine(v, v) == pytest.approx(1.0)
    assert vision.cosine(vision.normalize([1, 0]), vision.normalize([0, 1])) == 0


def test_visual_score_scales_and_cuts_off():
    assert vision.visual_score(1.0) == 1.0
    assert vision.visual_score(0.75) == 0.5
    assert vision.visual_score(0.3) == 0.0   # zu unähnlich -> keine Punkte


def test_pin_affinity_uses_most_similar_pins():
    beige = vision.normalize([216, 195, 165])
    black = vision.normalize([30, 30, 30])
    green = vision.normalize([60, 160, 70])
    # Ein beiges Produkt passt zu den beigen Pins, auch wenn viele andere Pins grün sind
    assert vision.pin_affinity(beige, [beige, green, green, green], top=1) == pytest.approx(
        1.0, abs=1e-3)
    assert vision.pin_affinity(green, [beige, beige], top=1) < vision.pin_affinity(
        beige, [beige, beige], top=1)
    assert vision.pin_affinity(beige, []) == 0.0
    assert vision.pin_affinity(black, [black]) == pytest.approx(1.0, abs=1e-3)


# --- Speicher und Berechnen ----------------------------------------------------------------------

def test_index_stores_and_skips_known_and_broken_images(fake):
    embedder = FakeEmbedder()
    store = vision.EmbeddingStore(embedder.name)
    entries = [("product:a", img("d8c3a5")), ("product:b", "https://img.test/kaputt.jpg"),
               ("product:c", None)]
    assert vision.index(store, embedder, entries) == {"total": 3, "new": 1, "failed": 1}
    assert store.get("product:a", img("d8c3a5")) is not None

    # Nochmal: nichts Neues zu berechnen (nur das kaputte Bild wird erneut versucht)
    embedder.calls = 0
    vision.index(store, embedder, entries)
    assert embedder.calls == 1

    # Neue Bild-URL -> Vektor veraltet -> neu berechnen
    vision.index(store, embedder, [("product:a", img("1f1d1e"))])
    assert store.get("product:a", img("d8c3a5")) is None
    assert store.get("product:a", img("1f1d1e")) is not None


def test_store_saves_and_resets_on_other_model(fake):
    store = vision.EmbeddingStore("model-a")
    store.put("product:x", "u", [1.0])
    store.save()
    assert vision.EmbeddingStore("model-a").get("product:x") == [1.0]
    assert vision.EmbeddingStore("model-b").get("product:x") is None   # anderes Modell
    assert vision.EmbeddingStore.load_existing().model == "model-a"


def test_load_existing_without_file(fake):
    assert vision.EmbeddingStore.load_existing() is None


def test_index_all_products_and_pins(fake):
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        {"id": "p1", "title": "x", "image_url": img("d8c3a5")},
        {"id": "p2", "title": "y", "image_url": None},
    ]})
    result = vision.index_all(FakeEmbedder())
    assert result["products"] == {"total": 50, "new": 50, "failed": 0}
    assert result["pins"] == {"total": 2, "new": 1, "failed": 0}
    store = vision.EmbeddingStore.load_existing()
    assert len(store.vectors("product:")) == 50 and set(store.vectors("pin:")) == {"p1"}


def test_clip_embedder_explains_missing_packages():
    # Läuft nur, wenn die KI-Pakete NICHT installiert sind
    try:
        import transformers  # noqa: F401
        pytest.skip("KI-Pakete sind installiert")
    except ImportError:
        pass
    with pytest.raises(vision.VisionUnavailable, match="requirements-ai.txt"):
        vision.ClipEmbedder()


# --- Ranking mit Bildern -------------------------------------------------------------------------

def test_similar_products_with_vectors_finds_lookalikes_without_shared_words():
    base = make_product(id="base", category="Oberteile", colors=["beige"], style_tags=[])
    lookalike = make_product(id="look", category="Hosen", colors=[], style_tags=[])  # nichts gemeinsam
    other = make_product(id="other", category="Hosen", colors=[], style_tags=[])
    # Vektoren wie vom FakeEmbedder (RGB minus 128)
    vectors = {"base": vision.normalize([88, 67, 37]), "look": vision.normalize([86, 62, 32]),
               "other": vision.normalize([-108, -8, 72])}

    assert similar_products(base, [lookalike, other]) == []           # ohne Bilder: nichts
    result = similar_products(base, [lookalike, other], vectors=vectors)
    assert result[0]["id"] == "look" and result[0]["looks_similar"] is True
    assert "other" not in [r["id"] for r in result]                   # sieht anders aus


def test_apply_visual_without_store_changes_nothing():
    ranked = [{"id": "a", "score": 1.0, "price": 10}]
    assert vision.apply_visual(ranked, [], "mode", None) == ranked


def test_api_recommendations_use_images_when_indexed(fake, client):
    # Ein Pin ohne verwertbaren Text, aber mit schwarzem Bild
    storage.save_pins({"fetched_at": 1, "board_ids": ["111"], "pins": [
        {"id": "p1", "title": "fit 🤍", "description": "", "board_name": "Looks",
         "image_url": img("222222")},
    ]})
    without = client.get("/api/recommendations?department=mode").json()["products"]
    assert all(p["score"] == 0 for p in without)

    vision.index_all(FakeEmbedder())
    with_images = client.get("/api/recommendations?department=mode").json()["products"]
    top = with_images[0]
    assert "schwarz" in top["colors"] and top["looks_like_pins"] is True
    assert top["score"] > 0


def test_api_detail_uses_images_when_indexed(fake, client):
    vision.index_all(FakeEmbedder())
    similar = client.get("/api/products/prod-006").json()["similar"]   # Bomberjacke Schwarz
    assert any(item["looks_similar"] for item in similar)


# --- Messwerkzeug mit Bildern ------------------------------------------------------------------

def test_visual_recommenders_in_evaluate(fake):
    products = JsonProductSource().load()
    vision.index_all(FakeEmbedder())
    store = vision.EmbeddingStore.load_existing()
    recommenders = make_visual_recommenders(store, FakeEmbedder())
    # Pin ohne Text, Bild in der Farbe des Slip Dress (schwarz, #222222)
    cases = [{"id": "ohne-text", "department": "mode",
              "pin": {"title": "", "description": "", "image_url": img("222222")},
              "relevant": ["prod-010"]}]
    report = evaluate(cases, recommenders["Bilder"], products)
    assert report["no_signal"] == 0
    assert report["hit_at_k"] == 1.0          # unter den Top 5 (alle schwarzen Teile)
    assert evaluate(cases, recommenders["Text + Bilder"], products)["no_signal"] == 0

    # Ohne Bild-URL: kein Signal
    no_image = [{**cases[0], "pin": {"title": "", "description": ""}}]
    assert evaluate(no_image, recommenders["Bilder"], products)["no_signal"] == 1


def test_progress_line_and_intermediate_saves(capsys):
    from backend.vision import Progress

    class Store:
        saves = 0

        def save(self):
            Store.saves += 1

    progress = Progress("Produkte", Store(), every=2)
    progress(1, 4)
    progress(2, 4)
    progress(4, 4)
    out = capsys.readouterr().out
    assert "Produkte: 4 / 4 Bilder (100%) – fertig" in out and out.endswith("\n")
    assert Store.saves == 2
