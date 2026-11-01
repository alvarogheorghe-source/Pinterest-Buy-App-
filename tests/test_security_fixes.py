"""Regressionstests zur Sicherheitsprüfung (Nov. 2026): jede Lücke wird hier nachgestellt."""
import gzip
import io
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import analysis, feeds, photo, pin_colors, pinterest, safe_fetch, storage
from backend.analysis import _spawn as REAL_SPAWN
from backend.main import app


def login(client):
    response = client.get("/auth/login")
    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    assert client.get(f"/auth/callback?code=abc&state={state}").status_code == 307


def users_in_db() -> set[str]:
    with sqlite3.connect(storage.DATA_DIR / storage.DB_FILE) as db:
        return {user for (user,) in db.execute("SELECT DISTINCT user FROM data")}


# --- Admin: Passwort ändern beendet alte Anmeldungen --------------------------------------

def test_admin_session_ends_when_password_changes(fake, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "alt-dummy-passwort")
    client = TestClient(app)
    assert client.post("/api/admin/login", json={"password": "alt-dummy-passwort"}).status_code == 200
    assert client.get("/api/admin/shops").status_code == 200
    monkeypatch.setenv("ADMIN_PASSWORD", "neu-dummy-passwort")
    assert client.get("/api/admin/shops").status_code == 401


def test_admin_session_expires(fake, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "dummy-passwort")
    client = TestClient(app)
    client.post("/api/admin/login", json={"password": "dummy-passwort"})
    later = time.time() + 13 * 3600
    monkeypatch.setattr("backend.main.time.time", lambda: later)
    assert client.get("/api/admin/shops").status_code == 401


def test_old_style_admin_cookie_is_not_accepted(fake, monkeypatch):
    """Frühere Cookies enthielten nur admin=True – das reicht nicht mehr."""
    from backend import main
    monkeypatch.setenv("ADMIN_PASSWORD", "dummy-passwort")
    request = type("R", (), {"session": {"admin": True}})()
    assert main.is_admin(request) is False


# --- Konto-Wechsel ohne Abmelden: Daten bleiben beim richtigen Konto ----------------------

def test_second_pinterest_account_does_not_take_first_accounts_data(fake, monkeypatch):
    monkeypatch.setenv("MULTI_USER", "1")
    who = {"name": "dummy-a"}
    original = fake.handler

    def handler(request):
        if request.url.path == "/v5/user_account":
            return httpx.Response(200, json={"username": who["name"]})
        return original(request)
    monkeypatch.setattr(pinterest, "_http", lambda: httpx.Client(transport=httpx.MockTransport(handler)))

    shared = TestClient(app, follow_redirects=False)
    login(shared)
    shared.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})
    who["name"] = "dummy-b"
    login(shared)                                       # B meldet sich an, A nicht getrennt

    assert storage.linked_user_id("dummy-a") in users_in_db()    # A behält seine Daten
    assert shared.get("/api/feedback").json() == {}               # B sieht nichts von A
    other_device = TestClient(app, follow_redirects=False)
    who["name"] = "dummy-a"
    login(other_device)
    assert "prod-001" in other_device.get("/api/feedback").json()


# --- "Alle meine Daten löschen" während einer Analyse --------------------------------------

def test_delete_during_analysis_stays_deleted(fake, monkeypatch):
    monkeypatch.setenv("MULTI_USER", "1")
    monkeypatch.setattr(analysis, "_spawn", REAL_SPAWN)
    gate, entered, finished = threading.Event(), threading.Event(), threading.Event()
    monkeypatch.setattr(pin_colors, "fill_missing_colors", lambda pins: (entered.set(), gate.wait(10)))
    real_run = analysis.run
    monkeypatch.setattr(analysis, "run", lambda: (real_run(), finished.set()))

    client = TestClient(app, follow_redirects=False)
    login(client)
    uid = storage.linked_user_id("testuser")
    token = storage.set_user(uid)
    storage.save_pins({"fetched_at": 7, "pins": [{"id": "x1", "title": "dummy pin"}]})
    storage.reset_user(token)

    assert client.post("/api/analysis").status_code == 200
    assert entered.wait(5)
    client.delete("/api/me")
    gate.set()
    assert finished.wait(5)
    assert uid not in users_in_db()                      # nichts wurde zurückgeschrieben
    login(client)
    assert client.get("/api/pins").json()["pins"] == []


# --- Feeds: keine fremden Geheimnisse in Adressen -----------------------------------------

def test_feed_urls_only_get_feed_keys(monkeypatch):
    monkeypatch.setenv("AWIN_FEED_KEY", "dummy-key")
    monkeypatch.setenv("SESSION_SECRET", "dummy-session")
    assert "dummy-key" in feeds.resolve_url("https://productdata.awin.com/x/{AWIN_FEED_KEY}/")
    with pytest.raises(feeds.FeedError):
        feeds.resolve_url("https://other.example/f?x={SESSION_SECRET}")


def test_awin_list_only_accepts_awin_download_urls(monkeypatch):
    monkeypatch.setenv("AWIN_FEED_KEY", "dummy-key")
    monkeypatch.delenv("AWIN_AUTO_FEEDS", raising=False)
    body = ("Feed ID,Advertiser Name,Membership Status,Primary Region,URL\n"
            "1,Böse,active,DE,https://other.example/f?x={SESSION_SECRET}\n"
            "2,Gut,active,DE,https://productdata.awin.com/datafeed/download/apikey/k/fid/2/\n")
    monkeypatch.setattr(feeds, "download", lambda url: body.encode())
    assert [f["name"] for f in feeds.discover_awin()] == ["awin-2"]


def test_gzip_bomb_is_refused(monkeypatch):
    monkeypatch.setattr(feeds, "MAX_UNPACKED", 1000)
    assert feeds._gunzip(gzip.compress(b"a" * 500)) == b"a" * 500
    with pytest.raises(feeds.FeedError):
        feeds._gunzip(gzip.compress(b"a" * 5000))


# --- Bilder: keine internen Adressen, auch nicht über Weiterleitungen ---------------------

@pytest.mark.parametrize("url", ["http://127.0.0.1:8000/x.png", "http://169.254.169.254/latest",
                                 "http://10.0.0.5/a.jpg", "http://[::1]/a.jpg",
                                 "http://localhost/a.jpg", "file:///etc/passwd"])
def test_internal_image_urls_are_refused(url):
    with pytest.raises(safe_fetch.UnsafeUrl):
        safe_fetch.check_url(url)


def test_redirect_to_internal_address_is_refused():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.host == "93.184.216.34":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/meta"})
        return httpx.Response(200, content=b"geheim")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(safe_fetch.UnsafeUrl):
        safe_fetch.get("https://93.184.216.34/bild.jpg", client=client)
    assert requested == ["https://93.184.216.34/bild.jpg"]          # internes Ziel nie angefragt


def test_public_redirect_still_works():
    def handler(request):
        if request.url.path == "/alt.jpg":
            return httpx.Response(301, headers={"location": "/neu.jpg"})
        return httpx.Response(200, content=b"bild")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert safe_fetch.get("https://93.184.216.34/alt.jpg", client=client) == b"bild"


# --- Foto-Suche: kleine Datei mit riesiger Pixelzahl wird abgelehnt ------------------------

def test_photo_with_too_many_pixels_is_refused():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("L", (8000, 8000)).save(buffer, "PNG")          # ~200 KB, aber 64 Megapixel
    data = buffer.getvalue()
    assert len(data) < photo.MAX_BYTES
    with pytest.raises(photo.PhotoError, match="Pixel"):
        photo.check_image(data)


def test_normal_photo_is_fine():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (1200, 1600), "pink").save(buffer, "JPEG")
    photo.check_image(buffer.getvalue())
