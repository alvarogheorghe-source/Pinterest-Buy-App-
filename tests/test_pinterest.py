"""Tests für Schritt 2: Pinterest-Login, Token-Refresh und Boards.

Pinterest wird hier SIMULIERT (httpx.MockTransport) – es wird nichts ins Internet
geschickt und man braucht keine echten Zugangsdaten.

Starten mit:  pytest -v
"""

import base64
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import pinterest, storage
from backend.main import app


class FakePinterest:
    """Spielt den Pinterest-Server. Merkt sich alle Anfragen, die ankommen."""

    def __init__(self):
        self.requests = []
        self.valid_token = "access-1"   # welchen Access Token die "API" gerade akzeptiert
        self.refresh_ok = True          # schlägt der Refresh fehl?
        self.board_pages = [[{"id": "b1", "name": "Sommer Looks", "pin_count": 12}]]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path

        if path == "/v5/oauth/token":
            form = parse_qs(request.content.decode())
            if form["grant_type"] == ["refresh_token"] and not self.refresh_ok:
                return httpx.Response(400, json={"error": "invalid_grant"})
            # Bei jedem Token-Tausch gibt es einen neuen Access Token
            self.valid_token = f"access-{len(self.requests)}"
            return httpx.Response(200, json={
                "access_token": self.valid_token,
                "refresh_token": "refresh-xyz",
                "expires_in": 30 * 24 * 3600,
                "refresh_token_expires_in": 365 * 24 * 3600,
                "scope": pinterest.SCOPES,
            })

        # Alle anderen Endpunkte brauchen einen gültigen Bearer Token
        if request.headers.get("Authorization") != f"Bearer {self.valid_token}":
            return httpx.Response(401, json={"message": "unauthorized"})

        if path == "/v5/user_account":
            return httpx.Response(200, json={"username": "testuser"})

        if path == "/v5/boards":
            # Seitenweise Antwort: "bookmark" zeigt auf die nächste Seite
            page_index = int(request.url.params.get("bookmark") or 0)
            has_more = page_index + 1 < len(self.board_pages)
            return httpx.Response(200, json={
                "items": self.board_pages[page_index],
                "bookmark": str(page_index + 1) if has_more else None,
            })

        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """Richtet für jeden Test eine saubere Umgebung ein."""
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)  # Daten in Temp-Ordner
    monkeypatch.setenv("PINTEREST_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("PINTEREST_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("PINTEREST_REDIRECT_URI", "http://localhost:8000/auth/callback")

    fake = FakePinterest()
    transport = httpx.MockTransport(fake.handler)
    monkeypatch.setattr(pinterest, "_http", lambda: httpx.Client(transport=transport))
    return fake


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def save_tokens(access="access-1", expires_in=10 * 24 * 3600, refresh_expires_in=300 * 24 * 3600):
    """Hilfsfunktion: legt gespeicherte Tokens an, als wäre man schon eingeloggt."""
    storage.save_tokens({
        "access_token": access,
        "expires_at": time.time() + expires_in,
        "refresh_token": "refresh-xyz",
        "refresh_expires_at": time.time() + refresh_expires_in,
    })


# --- Login ---------------------------------------------------------------------------

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_redirects_to_pinterest(fake, client):
    response = client.get("/auth/login")
    assert response.status_code == 307

    url = urlparse(response.headers["location"])
    params = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == pinterest.AUTH_URL
    assert params["client_id"] == ["test-client-id"]
    assert params["scope"] == ["user_accounts:read,boards:read,pins:read"]
    assert params["response_type"] == ["code"]
    assert len(params["state"][0]) > 10


def test_callback_rejects_wrong_state(fake, client):
    client.get("/auth/login")  # setzt den echten state im Session-Cookie
    response = client.get("/auth/callback?code=abc&state=gefaelscht")
    assert response.status_code == 400
    assert storage.load_tokens() is None


def test_callback_exchanges_code_and_saves_tokens(fake, client):
    login = client.get("/auth/login")
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    response = client.get(f"/auth/callback?code=abc&state={state}")
    assert response.status_code == 307
    assert response.headers["location"] == "/"

    # Wurde der Code korrekt mit Basic Auth eingetauscht?
    token_request = fake.requests[0]
    form = parse_qs(token_request.content.decode())
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["abc"]
    expected_auth = base64.b64encode(b"test-client-id:test-secret").decode()
    assert token_request.headers["Authorization"] == f"Basic {expected_auth}"

    tokens = storage.load_tokens()
    assert tokens["access_token"] == fake.valid_token
    assert tokens["refresh_token"] == "refresh-xyz"
    assert tokens["expires_at"] > time.time() + 29 * 24 * 3600


def test_login_error_from_pinterest(fake, client):
    response = client.get("/auth/callback?error=access_denied")
    assert response.headers["location"] == "/?error=access_denied"


# --- Refresh -------------------------------------------------------------------------

def test_expiring_token_is_refreshed_automatically(fake, client):
    save_tokens(access="old", expires_in=60)  # läuft in 1 Minute ab
    fake.valid_token = "old"

    assert client.get("/api/boards").status_code == 200

    form = parse_qs(fake.requests[0].content.decode())
    assert form["grant_type"] == ["refresh_token"]
    assert form["refresh_token"] == ["refresh-xyz"]
    assert storage.load_tokens()["access_token"] == fake.valid_token != "old"


def test_401_triggers_one_refresh_and_retry(fake, client):
    save_tokens(access="revoked")  # sieht gültig aus, wird aber abgelehnt
    response = client.get("/api/boards")
    assert response.status_code == 200
    paths = [r.url.path for r in fake.requests]
    assert paths == ["/v5/boards", "/v5/oauth/token", "/v5/boards"]


def test_expired_refresh_token_requires_new_login(fake, client):
    save_tokens(expires_in=-10, refresh_expires_in=-10)
    response = client.get("/api/boards")
    assert response.status_code == 401
    assert storage.load_tokens() is None
    assert client.get("/api/me").json() == {"connected": False}


def test_rejected_refresh_requires_new_login(fake, client):
    save_tokens(expires_in=-10)
    fake.refresh_ok = False
    assert client.get("/api/boards").status_code == 401
    assert storage.load_tokens() is None


# --- Boards & Auswahl ----------------------------------------------------------------------

def test_me_shows_username(fake, client):
    assert client.get("/api/me").json() == {"connected": False}
    save_tokens()
    assert client.get("/api/me").json() == {"connected": True, "username": "testuser"}


def test_boards_are_loaded_across_pages(fake, client):
    save_tokens()
    fake.board_pages = [
        [{"id": "b1", "name": "Beige Basics", "pin_count": 3,
          "media": {"image_cover_url": "https://i.pinimg.com/x.jpg"}}],
        [{"id": "b2", "name": "Streetwear", "pin_count": 7}],
    ]
    boards = client.get("/api/boards").json()
    assert [b["id"] for b in boards] == ["b1", "b2"]
    assert boards[0]["cover_url"] == "https://i.pinimg.com/x.jpg"
    assert boards[1]["cover_url"] is None


def test_board_selection_is_saved(fake, client):
    save_tokens()
    response = client.post("/api/boards/selection", json={"board_ids": ["b1", "b1"]})
    assert response.json() == {"board_ids": ["b1"]}
    assert client.get("/api/boards/selection").json() == {"board_ids": ["b1"]}
    assert client.get("/api/boards").json()[0]["selected"] is True


def test_logout_deletes_tokens(fake, client):
    save_tokens()
    client.post("/auth/logout")
    assert storage.load_tokens() is None


def test_missing_config_gives_clear_error(fake, client, monkeypatch):
    monkeypatch.delenv("PINTEREST_CLIENT_ID")
    response = client.get("/auth/login")
    assert response.status_code == 500
    assert "PINTEREST_CLIENT_ID" in response.json()["detail"]
