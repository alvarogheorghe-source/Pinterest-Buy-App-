"""Tests für Schritt 2: Pinterest-Login, Token-Refresh und Boards.

Der simulierte Pinterest-Server und die Fixtures stehen in conftest.py.

Starten mit:  pytest -v
"""

import base64
import time
from urllib.parse import parse_qs, urlparse

from backend import pinterest, storage
from tests.conftest import save_tokens


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
    response = client.post("/api/boards/selection", json={"board_ids": ["111", "111"]})
    assert response.json() == {"board_ids": ["111"]}
    assert client.get("/api/boards/selection").json() == {"board_ids": ["111"]}
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
