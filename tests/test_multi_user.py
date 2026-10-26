"""Mehrere Personen (MULTI_USER=1): jede sieht nur ihre eigenen Daten."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from backend import analysis, storage, vision
from backend.analysis import _spawn as REAL_SPAWN   # echte Thread-Funktion (vor dem Test-Patch)
from backend.main import app
from tests.test_analysis import FakeEmbedder


@pytest.fixture
def two_people(fake, monkeypatch):
    """Zwei Browser mit je eigenem Cookie."""
    monkeypatch.setenv("MULTI_USER", "1")
    return TestClient(app), TestClient(app)


def pins(*titles):
    return {"fetched_at": 1, "board_ids": ["x"],
            "pins": [{"id": f"p{i}", "title": t} for i, t in enumerate(titles)]}


def test_merkliste_is_separate(two_people):
    anna, ben = two_people
    assert anna.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"}).status_code == 200
    assert "prod-001" in anna.get("/api/feedback").json()
    assert ben.get("/api/feedback").json() == {}                 # Ben sieht Annas Merkliste nicht
    assert [p["id"] for p in anna.get("/api/saved").json()] == ["prod-001"]
    assert ben.get("/api/saved").json() == []


def test_pinterest_connection_is_separate(two_people):
    anna, ben = two_people
    anna.get("/api/feedback")                                     # Anna bekommt ihre Kennung
    # Anna "verbindet" Pinterest: Tokens für ihre Kennung speichern
    token = storage.set_user(_uid(anna))
    storage.save_tokens({"access_token": "a", "expires_at": time.time() + 999,
                         "refresh_token": "r", "refresh_expires_at": time.time() + 9999})
    storage.save_pins(pins("goth jacket", "black boots"))
    storage.reset_user(token)

    assert anna.get("/", follow_redirects=False).status_code == 307   # Anna -> Shop
    assert ben.get("/", follow_redirects=False).status_code == 200    # Ben -> Startseite
    assert len(anna.get("/api/pins").json()["pins"]) == 2
    assert ben.get("/api/pins").json()["pins"] == []
    assert anna.get("/api/vibe").json()["title"] == "Goth Baddie"
    assert ben.get("/api/vibe").json()["title"] == "Noch ein Geheimnis"


def _uid(client) -> str:
    """Kennung aus dem signierten Session-Cookie lesen (nur für den Test)."""
    import base64
    raw = client.cookies.get("session").split(".")[0]
    return json.loads(base64.b64decode(raw + "=="))["uid"]


def test_delete_my_data(two_people):
    anna, ben = two_people
    anna.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})
    ben.post("/api/feedback", json={"product_id": "prod-002", "vote": "like"})
    assert anna.delete("/api/me").json()["removed"] >= 1
    assert anna.get("/api/feedback").json() == {}
    assert "prod-002" in ben.get("/api/feedback").json()         # Bens Daten bleiben


def test_background_analysis_works_for_the_right_person(two_people, monkeypatch):
    """Die Analyse läuft in einem eigenen Thread – und muss trotzdem Annas Pins anschauen."""
    anna, ben = two_people
    monkeypatch.setattr(analysis, "_spawn", REAL_SPAWN)        # wirklich im Hintergrund-Thread
    monkeypatch.setattr(vision, "get_embedder", FakeEmbedder)
    anna.get("/api/feedback")
    token = storage.set_user(_uid(anna))
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "a1", "title": "", "image_url": "https://img.test/a1.jpg"}]})
    storage.reset_user(token)

    assert anna.post("/api/analysis").status_code == 200
    for _ in range(100):                                         # auf den Thread warten
        if anna.get("/api/analysis").json()["status"] != "running":
            break
        time.sleep(0.05)
    assert anna.get("/api/analysis").json()["status"] == "done"
    assert anna.get("/api/pins").json()["pins"][0]["image_styles"] == ["goth"]
    assert ben.get("/api/analysis").json()["status"] == "idle"   # Ben: keine Analyse


def test_local_mode_is_one_person(fake, client):
    """Ohne MULTI_USER: alle Browser (und die Terminal-Befehle) sind dieselbe Person."""
    other = TestClient(app)
    client.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})
    assert "prod-001" in other.get("/api/feedback").json()


def test_old_json_files_are_moved_into_the_database(fake):
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (storage.DATA_DIR / "feedback.json").write_text(json.dumps({"prod-009": {"vote": "like"}}))
    assert storage.read_json("feedback.json") == {"prod-009": {"vote": "like"}}
    assert not (storage.DATA_DIR / "feedback.json").exists()
    assert (storage.DATA_DIR / storage.LEGACY_FOLDER / "feedback.json").exists()


def pinterest_login(client):
    """Kompletter Login wie im Browser (Pinterest ist simuliert)."""
    from urllib.parse import parse_qs, urlparse
    login = client.get("/auth/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    assert client.get(f"/auth/callback?code=abc&state={state}", follow_redirects=False).status_code == 307


def test_same_pinterest_account_same_data_on_every_device(two_people):
    handy, laptop = two_people                      # dieselbe Person, zwei Geräte
    handy.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})   # noch anonym
    pinterest_login(handy)
    assert handy.get("/api/me").json()["connected"] is True
    assert "prod-001" in handy.get("/api/feedback").json()    # anonym Gemerktes ist übernommen

    laptop.post("/api/feedback", json={"product_id": "prod-002", "vote": "like"})
    assert "prod-001" not in laptop.get("/api/feedback").json()  # vor dem Login: getrennt
    pinterest_login(laptop)
    assert set(laptop.get("/api/feedback").json()) == {"prod-001", "prod-002"}  # zusammengeführt
    assert set(handy.get("/api/feedback").json()) == {"prod-001", "prod-002"}   # gleich überall


def test_disconnect_on_shared_device_hides_everything(two_people):
    laptop, _ = two_people
    laptop.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})
    pinterest_login(laptop)
    laptop.post("/auth/logout")
    assert laptop.get("/api/feedback").json() == {}              # nächste Person sieht nichts
    assert laptop.get("/api/me").json()["connected"] is False
    pinterest_login(laptop)                                       # wieder einloggen
    assert "prod-001" in laptop.get("/api/feedback").json()      # alles wieder da


def test_pinterest_id_is_not_stored_in_plain_text(two_people):
    handy, _ = two_people
    pinterest_login(handy)
    import sqlite3
    with sqlite3.connect(storage.DATA_DIR / storage.DB_FILE) as db:
        users = {row[0] for row in db.execute("SELECT user FROM data")}
    assert users and all("testuser" not in user for user in users)
