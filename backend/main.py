"""Einstiegspunkt der FastAPI-App.

Starten mit:  uvicorn backend.main:app --reload
"""

import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from backend import pins, pinterest, storage
from backend.config import FRONTEND_DIR, ConfigError

app = FastAPI(title="Style App")

# Session-Cookie: merkt sich den OAuth-"state" zwischen Login und Callback.
# Das Cookie wird mit SESSION_SECRET signiert, damit niemand es fälschen kann.
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    print("WARNUNG: SESSION_SECRET fehlt in .env – nutze einen zufälligen Wert für diesen Start.")
    session_secret = secrets.token_hex(32)
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax")


# --- Fehlerbehandlung -------------------------------------------------------------

@app.exception_handler(pinterest.NotConnectedError)
def not_connected(request: Request, exc: pinterest.NotConnectedError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(ConfigError)
def config_missing(request: Request, exc: ConfigError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# --- Allgemein ----------------------------------------------------------------------

@app.get("/health")
def health():
    """Kleiner Check, ob der Server läuft."""
    return {"status": "ok"}


# --- Login mit Pinterest (OAuth) -------------------------------------------------------

@app.get("/auth/login")
def login(request: Request):
    """Schickt den Nutzer zum Einloggen zu Pinterest."""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(pinterest.build_login_url(state))


@app.get("/auth/callback")
def callback(request: Request, code: str | None = None, state: str | None = None,
             error: str | None = None):
    """Hierher schickt Pinterest den Nutzer nach dem Login zurück."""
    if error:
        # z.B. wenn der Nutzer auf "Ablehnen" geklickt hat
        return RedirectResponse(f"/?error={error}")

    expected_state = request.session.pop("oauth_state", None)
    if not state or state != expected_state:
        raise HTTPException(400, "Ungültiger state – bitte Login neu starten.")
    if not code:
        raise HTTPException(400, "Kein Code von Pinterest erhalten.")

    pinterest.exchange_code(code)
    return RedirectResponse("/")


@app.post("/auth/logout")
def logout():
    """Trennt die Verbindung, indem die gespeicherten Tokens gelöscht werden."""
    storage.delete_tokens()
    return {"ok": True}


# --- API für das Frontend ----------------------------------------------------------------

@app.get("/api/me")
def me():
    """Ist der Nutzer verbunden? Wenn ja: mit welchem Konto?"""
    if not storage.load_tokens():
        return {"connected": False}
    try:
        account = pinterest.get_user_account()
    except pinterest.NotConnectedError:
        return {"connected": False}
    return {"connected": True, "username": account.get("username")}


@app.get("/api/boards")
def boards():
    """Alle Boards + welche davon ausgewählt sind."""
    selected = set(storage.load_selected_boards())
    result = pinterest.list_boards()
    for board in result:
        board["selected"] = board["id"] in selected
    return result


class BoardSelection(BaseModel):
    """So muss die Anfrage zum Speichern aussehen: {"board_ids": ["123", "456"]}"""
    board_ids: list[str]


@app.get("/api/boards/selection")
def get_selection():
    return {"board_ids": storage.load_selected_boards()}


@app.post("/api/boards/selection")
def save_selection(selection: BoardSelection):
    # Pinterest-Board-IDs bestehen nur aus Ziffern. Wir prüfen das, weil die ID
    # später in die Adresse der API-Abfrage eingesetzt wird (/boards/<id>/pins).
    if not all(board_id.isdigit() for board_id in selection.board_ids):
        raise HTTPException(400, "Ungültige Board-ID.")
    # dict.fromkeys entfernt Duplikate und behält die Reihenfolge
    board_ids = list(dict.fromkeys(selection.board_ids))
    storage.save_selected_boards(board_ids)
    return {"board_ids": board_ids}


@app.post("/api/pins/refresh")
def refresh_pins():
    """Lädt die Pins der ausgewählten Boards neu von Pinterest."""
    try:
        data = pins.load_pins_for_selected_boards()
    except ValueError as err:
        raise HTTPException(400, str(err))
    return {"count": len(data["pins"]), "board_count": len(data["board_ids"])}


@app.get("/api/pins")
def get_pins():
    """Die zuletzt gespeicherten Pins (ohne neue Anfrage an Pinterest)."""
    return storage.load_pins()


# Das Frontend (HTML/CSS/JS) wird direkt vom Backend ausgeliefert.
# Muss als LETZTES kommen, sonst würde es die API-Routen überdecken.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
