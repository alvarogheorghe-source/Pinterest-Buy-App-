"""Gemeinsame Test-Hilfen. pytest lädt diese Datei automatisch.

Pinterest wird hier SIMULIERT (httpx.MockTransport) – es wird nichts ins Internet
geschickt und man braucht keine echten Zugangsdaten.
"""

import time
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import pinterest, storage
from backend.main import app


def paged(pages: list[list[dict]], request: httpx.Request) -> httpx.Response:
    """Seitenweise Antwort wie bei Pinterest: "bookmark" zeigt auf die nächste Seite."""
    page_index = int(request.url.params.get("bookmark") or 0)
    has_more = page_index + 1 < len(pages)
    return httpx.Response(200, json={
        "items": pages[page_index],
        "bookmark": str(page_index + 1) if has_more else None,
    })


class FakePinterest:
    """Spielt den Pinterest-Server. Merkt sich alle Anfragen, die ankommen."""

    def __init__(self):
        self.requests = []
        self.valid_token = "access-1"   # welchen Access Token die "API" gerade akzeptiert
        self.refresh_ok = True          # schlägt der Refresh fehl?
        self.board_pages = [[{"id": "111", "name": "Sommer Looks", "pin_count": 12}]]
        self.board_pins = {}            # Board-ID -> Liste von Seiten mit Pins

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
            return paged(self.board_pages, request)

        # /v5/boards/<id>/pins
        parts = path.split("/")
        if len(parts) == 5 and parts[2] == "boards" and parts[4] == "pins":
            pages = self.board_pins.get(parts[3])
            if pages is None:
                return httpx.Response(404, json={"message": "board not found"})
            return paged(pages, request)

        return httpx.Response(404)


@pytest.fixture(autouse=True)
def demo_products(monkeypatch):
    """Tests nutzen IMMER die Beispielprodukte – auch wenn in .env eBay-Schlüssel stehen."""
    monkeypatch.setenv("PRODUCT_SOURCE", "demo")


@pytest.fixture(autouse=True)
def no_background_analysis(monkeypatch):
    """Malis Hintergrund-Analyse startet in Tests nicht von selbst (test_analysis.py testet sie)."""
    from backend import analysis
    analysis._states.clear()
    monkeypatch.setattr(analysis, "_spawn", lambda target: None)


@pytest.fixture(autouse=True)
def no_exchange_rate_downloads(monkeypatch):
    """Wechselkurse: in Tests nie die EZB fragen – die festen Ersatzkurse gelten."""
    from backend import currency
    monkeypatch.setattr(currency, "_refresh_in_background", lambda: None)


@pytest.fixture(autouse=True)
def no_image_downloads(monkeypatch):
    """Pin-Bilder werden in Tests nie wirklich geladen (backend/pin_colors.py)."""
    from backend import pin_colors
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    monkeypatch.setattr(pin_colors, "_http", lambda: httpx.Client(transport=transport))


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
