"""Awin-Verbindung prüfen (backend/awin.py) – Awin wird simuliert."""

import httpx
import pytest

from backend import awin


@pytest.fixture
def fake_awin(monkeypatch):
    monkeypatch.setenv("AWIN_API_TOKEN", "token-123")
    monkeypatch.setenv("AWIN_PUBLISHER_ID", "4711")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.headers["Authorization"] != "Bearer token-123":
            return httpx.Response(401)
        assert request.url.path == "/publishers/4711/programmes"
        joined = [{"id": 1, "name": "Mode Shop", "primaryRegion": {"countryCode": "AT"}}]
        return httpx.Response(200, json=joined if request.url.params["relationship"] == "joined" else [])

    monkeypatch.setattr(awin, "_http", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    return calls


def test_lists_joined_programmes(fake_awin, capsys):
    awin.main()
    out = capsys.readouterr().out
    assert "Verbindung zu Awin: ok" in out and "Mode Shop  (AT, ID 1)" in out
    assert "Wartet auf Antwort (0)" in out


def test_wrong_token_gives_clear_message(fake_awin, monkeypatch, capsys):
    monkeypatch.setenv("AWIN_API_TOKEN", "falsch")
    awin.main()
    assert "AWIN_API_TOKEN" in capsys.readouterr().out


def test_not_configured(monkeypatch, capsys):
    monkeypatch.delenv("AWIN_API_TOKEN", raising=False)
    awin.main()
    assert "fehlen in .env" in capsys.readouterr().out
