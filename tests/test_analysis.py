"""Tests für Malis Hintergrund-Analyse (backend/analysis.py) – mit simuliertem KI-Modell."""

import pytest

from backend import analysis, storage, vision
from tests.test_image_tags import LABELS, FakeTextEmbedder, axis


class FakeEmbedder(FakeTextEmbedder):
    """Bilder: jedes Bild zeigt eine Jacke im Goth-Stil."""

    def __init__(self):
        super().__init__()
        self.images = 0

    def embed_image_urls(self, urls):
        self.images += len(urls)
        return [None if "kaputt" in url else axis(("style:goth", 1.0), ("category:Jacken", 1.0))
                for url in urls]


@pytest.fixture
def run_now(monkeypatch):
    """Analyse sofort statt im Hintergrund-Thread."""
    monkeypatch.setattr(analysis, "_spawn", lambda target: target())


def save_board(n=3):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": str(i), "title": "", "image_url": f"https://img.test/{i}.jpg"} for i in range(n)]})


def test_full_analysis_with_progress(fake, client, run_now, monkeypatch):
    embedder = FakeEmbedder()
    monkeypatch.setattr(vision, "get_embedder", lambda: embedder)
    save_board()
    assert client.get("/api/analysis").json()["needed"] is True

    result = client.post("/api/analysis").json()
    assert result["status"] == "done" and result["vision"] is True and result["needed"] is False
    assert result["found"][:2] == ["goth", "Jacken"]                # "Ich hab … entdeckt!"
    pin = storage.load_pins()["pins"][0]
    assert pin["image_styles"] == ["goth"] and pin["image_categories"] == ["Jacken"]
    assert client.get("/api/vibe").json()["title"] == "Goth Baddie"  # ohne Terminal!

    # Nochmal: nichts Neues zu rechnen
    images = embedder.images
    client.post("/api/analysis")
    assert embedder.images == images


def test_without_ai_packages_only_colors(fake, client, run_now, monkeypatch):
    def unavailable():
        raise vision.VisionUnavailable("KI-Pakete fehlen")
    monkeypatch.setattr(vision, "get_embedder", unavailable)
    save_board()
    result = client.post("/api/analysis").json()
    assert result["status"] == "done" and result["vision"] is False and result["needed"] is False


def test_errors_are_reported_not_crashing(fake, client, run_now, monkeypatch):
    def broken():
        raise RuntimeError("Festplatte voll")
    monkeypatch.setattr(vision, "get_embedder", broken)
    save_board()
    result = client.post("/api/analysis").json()
    assert result["status"] == "error" and "Festplatte voll" in result["error"]


def test_new_pins_need_a_new_analysis(fake, client, run_now, monkeypatch):
    monkeypatch.setattr(vision, "get_embedder", FakeEmbedder)
    save_board(2)
    client.post("/api/analysis")
    assert client.get("/api/analysis").json()["needed"] is False
    save_board(3)
    assert client.get("/api/analysis").json()["needed"] is True


def test_loading_pins_starts_the_analysis(fake, client, monkeypatch):
    from tests.conftest import save_tokens
    started = []
    monkeypatch.setattr(analysis, "_spawn", started.append)
    save_tokens()
    storage.save_selected_boards(["111"])
    fake.board_pins["111"] = [[{"id": "p1", "title": "Pin"}]]
    client.post("/api/pins/refresh")
    assert len(started) == 1
    assert client.get("/api/analysis").json()["status"] == "running"


def test_no_analysis_without_pins(fake, client):
    assert client.post("/api/analysis").status_code == 400


def test_interrupted_analysis_is_not_stuck(fake):
    storage.write_json("analysis.json", {"status": "running", "step": "bilder"})
    analysis._state.clear()
    assert analysis.status()["status"] == "idle"
