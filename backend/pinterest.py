"""Verbindung zur offiziellen Pinterest API v5 (OAuth 2.0).

Ablauf:
1. build_login_url()      -> Nutzer wird zu Pinterest geschickt und loggt sich DORT ein
2. exchange_code()        -> Pinterest schickt uns einen "code", den tauschen wir gegen Tokens
3. get_valid_access_token -> vor jedem API-Aufruf: Token noch gültig? Sonst erneuern (Refresh)
4. api_get()              -> eigentliche API-Aufrufe (z.B. Boards)

Doku: https://developers.pinterest.com/docs/getting-started/authentication/
"""

import time
from urllib.parse import urlencode

import httpx

from backend import storage
from backend.config import get_setting

AUTH_URL = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
API_BASE = "https://api.pinterest.com/v5"

# Nur Lese-Rechte – mehr brauchen wir nicht
SCOPES = "user_accounts:read,boards:read,pins:read"

# Token schon erneuern, wenn er in weniger als 1 Tag abläuft
REFRESH_MARGIN_SECONDS = 24 * 60 * 60


class NotConnectedError(Exception):
    """Kein gültiger Login vorhanden -> Nutzer muss sich (neu) verbinden."""


def _http() -> httpx.Client:
    """Erzeugt den HTTP-Client. Eigene Funktion, damit Tests Pinterest simulieren können."""
    return httpx.Client(timeout=15)


# --- Schritt 1: Login-URL -----------------------------------------------------

def build_login_url(state: str) -> str:
    """Baut die URL, auf die wir den Nutzer zum Einloggen schicken.

    `state` ist ein Zufallswert. Pinterest schickt ihn unverändert zurück,
    so erkennen wir, dass der Callback wirklich zu unserem Login gehört.
    """
    params = {
        "client_id": get_setting("PINTEREST_CLIENT_ID"),
        "redirect_uri": get_setting("PINTEREST_REDIRECT_URI"),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


# --- Schritt 2: Tokens holen und erneuern ----------------------------------------

def _request_token(form_data: dict) -> dict:
    """Schickt eine Anfrage an den Token-Endpunkt.

    Pinterest will Client-ID und Secret per "HTTP Basic Auth".
    """
    auth = (get_setting("PINTEREST_CLIENT_ID"), get_setting("PINTEREST_CLIENT_SECRET"))
    with _http() as client:
        response = client.post(TOKEN_URL, data=form_data, auth=auth)
    response.raise_for_status()
    return response.json()


def _save_token_response(data: dict, old_tokens: dict | None = None) -> dict:
    """Rechnet aus "läuft in X Sekunden ab" einen festen Zeitpunkt aus und speichert."""
    now = time.time()
    old_tokens = old_tokens or {}
    tokens = {
        "access_token": data["access_token"],
        "expires_at": now + data.get("expires_in", 0),
        # Bei einem Refresh schickt Pinterest manchmal keinen neuen Refresh Token,
        # dann behalten wir den alten.
        "refresh_token": data.get("refresh_token") or old_tokens.get("refresh_token"),
        "refresh_expires_at": (
            now + data["refresh_token_expires_in"]
            if "refresh_token_expires_in" in data
            else old_tokens.get("refresh_expires_at")
        ),
        "scope": data.get("scope"),
    }
    storage.save_tokens(tokens)
    return tokens


def exchange_code(code: str) -> dict:
    """Tauscht den einmaligen Code aus dem Callback gegen Access + Refresh Token."""
    data = _request_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_setting("PINTEREST_REDIRECT_URI"),
    })
    return _save_token_response(data)


def refresh_access_token() -> dict:
    """Holt mit dem Refresh Token einen neuen Access Token (ohne neuen Login)."""
    tokens = storage.load_tokens()
    if not tokens or not tokens.get("refresh_token"):
        raise NotConnectedError("Kein Refresh Token vorhanden.")

    # Ist auch der Refresh Token abgelaufen, hilft nur ein neuer Login
    refresh_expires = tokens.get("refresh_expires_at")
    if refresh_expires and refresh_expires < time.time():
        storage.delete_tokens()
        raise NotConnectedError("Refresh Token abgelaufen – bitte neu verbinden.")

    try:
        data = _request_token({
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        })
    except httpx.HTTPStatusError as err:
        # Pinterest lehnt den Refresh Token ab (z.B. Zugriff entzogen)
        storage.delete_tokens()
        raise NotConnectedError("Refresh fehlgeschlagen – bitte neu verbinden.") from err
    return _save_token_response(data, old_tokens=tokens)


def get_valid_access_token() -> str:
    """Gibt einen gültigen Access Token zurück und erneuert ihn bei Bedarf."""
    tokens = storage.load_tokens()
    if not tokens:
        raise NotConnectedError("Nicht mit Pinterest verbunden.")
    if tokens["expires_at"] - time.time() < REFRESH_MARGIN_SECONDS:
        tokens = refresh_access_token()
    return tokens["access_token"]


# --- Schritt 3: API-Aufrufe ---------------------------------------------------------

def api_get(path: str, params: dict | None = None) -> dict:
    """GET-Anfrage an die Pinterest API mit automatischem Refresh.

    Falls Pinterest trotzdem 401 (nicht autorisiert) antwortet, erneuern wir
    den Token einmal und versuchen es noch einmal.
    """
    def send(token: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        with _http() as client:
            return client.get(f"{API_BASE}{path}", params=params, headers=headers)

    response = send(get_valid_access_token())
    if response.status_code == 401:
        response = send(refresh_access_token()["access_token"])
        if response.status_code == 401:
            raise NotConnectedError("Pinterest akzeptiert den Token nicht.")
    response.raise_for_status()
    return response.json()


def get_user_account() -> dict:
    """Infos zum eingeloggten Konto (z.B. Benutzername)."""
    return api_get("/user_account")


def list_boards() -> list[dict]:
    """Alle Boards des Nutzers.

    Pinterest liefert Ergebnisse seitenweise. Solange ein "bookmark" zurückkommt,
    gibt es noch eine weitere Seite.
    """
    boards = []
    bookmark = None
    while True:
        params = {"page_size": 100}
        if bookmark:
            params["bookmark"] = bookmark
        page = api_get("/boards", params=params)

        for board in page.get("items", []):
            boards.append({
                "id": board["id"],
                "name": board.get("name", ""),
                "description": board.get("description", ""),
                "pin_count": board.get("pin_count", 0),
                "cover_url": (board.get("media") or {}).get("image_cover_url"),
            })

        bookmark = page.get("bookmark")
        if not bookmark:
            return boards
