"""Tests für Schritt 3: Pins der ausgewählten Boards laden und speichern.

Starten mit:  pytest -v
"""

from backend import pins, storage
from tests.conftest import save_tokens


def make_pin(pin_id, title="", description="", images=None, color=None, link=None):
    """Baut einen Pin so, wie ihn die Pinterest API liefert."""
    return {
        "id": pin_id,
        "title": title,
        "description": description,
        "dominant_color": color,
        "link": link,
        "media": {"media_type": "image", "images": images or {}},
    }


def test_pins_are_loaded_saved_and_simplified(fake, client):
    save_tokens()
    storage.save_selected_boards(["111"])
    fake.board_pins["111"] = [[
        make_pin("p1", "Beiger Oversized Hoodie", "cozy streetwear",
                 images={"150x150": {"url": "small.jpg"}, "600x": {"url": "big.jpg"}},
                 color="#d8c3a5", link="https://www.depop.com/products/seller-beige-hoodie/"),
    ]]

    response = client.post("/api/pins/refresh")
    assert response.json() == {"count": 1, "board_count": 1}

    saved = client.get("/api/pins").json()
    assert saved["pins"] == [{
        "id": "p1",
        "board_id": "111",
        "title": "Beiger Oversized Hoodie",
        "description": "cozy streetwear",
        "image_url": "big.jpg",   # 600x wird gegenüber 150x150 bevorzugt
        "dominant_color": "#d8c3a5",
        "link": "https://www.depop.com/products/seller-beige-hoodie/",
    }]
    assert saved["fetched_at"] is not None


def test_pins_are_loaded_across_pages_and_boards(fake, client):
    save_tokens()
    storage.save_selected_boards(["111", "222"])
    fake.board_pins["111"] = [[make_pin("p1")], [make_pin("p2")]]  # 2 Seiten
    fake.board_pins["222"] = [[make_pin("p3"), make_pin("p1")]]     # p1 doppelt

    assert client.post("/api/pins/refresh").json() == {"count": 3, "board_count": 2}
    ids = [p["id"] for p in storage.load_pins()["pins"]]
    assert ids == ["p1", "p2", "p3"]  # Duplikat nur einmal gespeichert


def test_max_pins_per_board_is_respected(fake, monkeypatch):
    save_tokens()
    fake.board_pins["111"] = [[make_pin(f"a{i}") for i in range(3)],
                              [make_pin(f"b{i}") for i in range(3)],
                              [make_pin(f"c{i}") for i in range(3)]]

    result = pins.fetch_board_pins("111", max_pins=4)
    assert [p["id"] for p in result] == ["a0", "a1", "a2", "b0"]
    # Nach Seite 2 ist das Maximum erreicht -> Seite 3 wird gar nicht erst abgefragt
    assert len([r for r in fake.requests if r.url.path.endswith("/pins")]) == 2


def test_refresh_without_selected_boards_gives_clear_error(fake, client):
    save_tokens()
    response = client.post("/api/pins/refresh")
    assert response.status_code == 400
    assert response.json()["detail"] == "Keine Boards ausgewählt."


def test_refresh_without_login_gives_401(fake, client):
    storage.save_selected_boards(["111"])
    assert client.post("/api/pins/refresh").status_code == 401


def test_no_pins_saved_yet(fake, client):
    assert client.get("/api/pins").json() == {"fetched_at": None, "pins": []}


def test_invalid_board_ids_are_rejected(fake, client):
    response = client.post("/api/boards/selection", json={"board_ids": ["../user_account"]})
    assert response.status_code == 400
    assert storage.load_selected_boards() == []


def test_pick_image_url_variants():
    assert pins.pick_image_url(None) is None
    assert pins.pick_image_url({"images": {"originals": {"url": "o.jpg"}}}) == "o.jpg"
    # Video-Pin: kein "images", aber ein Vorschaubild
    assert pins.pick_image_url({"media_type": "video", "cover_image_url": "v.jpg"}) == "v.jpg"
