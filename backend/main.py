"""Einstiegspunkt der FastAPI-App.

Starten mit:  uvicorn backend.main:app --reload
"""

import os
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from backend import (analysis, feedback, matching, pins, pinterest, products, shop_links,
                     similar, storage, vibe, vision)
from backend.config import FRONTEND_DIR, ConfigError

app = FastAPI(title="Malipin")

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


@app.exception_handler(products.ProductSourceError)
def products_broken(request: Request, exc: products.ProductSourceError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


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
        return RedirectResponse(f"/konto.html?error={error}")

    expected_state = request.session.pop("oauth_state", None)
    if not state or state != expected_state:
        raise HTTPException(400, "Ungültiger state – bitte Login neu starten.")
    if not code:
        raise HTTPException(400, "Kein Code von Pinterest erhalten.")

    pinterest.exchange_code(code)
    # Nach dem Login direkt zur Board-Auswahl
    return RedirectResponse("/konto.html")


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
    # Mali schaut sich die neuen Pins gleich im Hintergrund an (Farben, Bilder, Stil, Marken)
    analysis.start()
    return {"count": len(data["pins"]), "board_count": len(data["board_ids"])}


@app.get("/api/analysis")
def get_analysis():
    """Wie weit ist Malis Analyse? (Schritt, Fortschritt, was gefunden wurde, ob nötig)"""
    return analysis.status()


@app.post("/api/analysis")
def start_analysis():
    """Analyse starten (z.B. nach einem RSS-Import). Läuft sie schon, passiert nichts."""
    if not storage.load_pins()["pins"]:
        raise HTTPException(400, "Noch keine Pins geladen.")
    return analysis.start()


@app.get("/api/pins")
def get_pins():
    """Die zuletzt gespeicherten Pins (ohne neue Anfrage an Pinterest)."""
    return storage.load_pins()


@app.get("/api/pin-items")
def get_pin_items(max_price: float | None = None,
                  department: products.Department | None = None):
    """Pins, die direkt zu einem Shop oder Marktplatz (z.B. Depop) führen.
    Beispiel: /api/pin-items?max_price=30&department=wohnen"""
    items = shop_links.find_pin_items(storage.load_pins()["pins"])
    if department:
        items = [item for item in items if item["department"] == department]
    return shop_links.filter_by_budget(items, max_price)


# --- Produkte (Schritt 4) -------------------------------------------------------------

@app.get("/api/products")
def get_products(min_price: float | None = None, max_price: float | None = None,
                 category: str | None = None,
                 department: products.Department | None = None):
    """Produkte, optional gefiltert. Beispiel: /api/products?max_price=30&department=wohnen"""
    all_products = products.get_product_source().load()
    return products.filter_products(all_products, min_price, max_price, category, department)


@app.get("/api/products/{product_id}")
def get_product_detail(product_id: str, limit: int = Query(12, ge=1, le=48)):
    """Ein Produkt mit Begründung + ähnliche Artikel ("Mehr wie das").
    Beispiel: /api/products/prod-001"""
    all_products = products.get_product_source().load()
    product = next((p for p in all_products if p.id == product_id), None)
    if product is None:
        raise HTTPException(404, "Produkt nicht gefunden.")

    # Begründung wie im Shop: mit dem Stilprofil der passenden Welt
    profile = matching.build_style_profile(storage.load_pins()["pins"], product.department)
    detail = matching.rank_products([product], profile)[0]

    # 👍/👎: eigene Bewertung anzeigen, mit 👎 bewertete Produkte nicht vorschlagen
    votes = feedback.load_feedback()
    detail["vote"] = votes.get(product_id, {}).get("vote")
    disliked = feedback.ids_with_vote(votes, "dislike")
    # Bild-Vektoren, falls schon berechnet (python -m backend.vision) – sonst nur Text
    store = vision.EmbeddingStore.load_existing()
    vectors = store.vectors("product:") if store else None
    similar_items = [item for item in similar.similar_products(product, all_products, limit=48,
                                                               vectors=vectors)
                     if item["id"] not in disliked][:limit]
    for item in similar_items:
        item["vote"] = votes.get(item["id"], {}).get("vote")
    return {
        "product": detail,
        "has_profile": profile.pin_count > 0,
        "similar": similar_items,
    }


@app.get("/api/categories")
def get_categories(department: products.Department | None = None):
    """Kategorien, z.B. /api/categories?department=wohnen"""
    return products.list_categories(products.get_product_source().load(), department)


# --- Matching (Schritt 5) ---------------------------------------------------------------

@app.get("/api/profile")
def get_profile():
    """Die Stilprofile aus den gespeicherten Pins – getrennt für Mode und Wohnen."""
    pins_list = storage.load_pins()["pins"]
    return {
        department: matching.build_style_profile(pins_list, department).to_dict()
        for department in products.DEPARTMENTS
    }


@app.get("/api/recommendations")
def get_recommendations(min_price: float | None = None, max_price: float | None = None,
                        category: str | None = None,
                        department: products.Department = "mode"):
    """Produkte einer Welt im Budget, sortiert nach Passung zum Stilprofil dieser Welt."""
    pins_list = storage.load_pins()["pins"]
    profile = matching.build_style_profile(pins_list, department)
    all_products = products.get_product_source().load()
    selection = products.filter_products(all_products, min_price, max_price, category,
                                         department)
    ranked = matching.rank_products(selection, profile)
    # Bilder: "sieht aus wie deine Pins" (nur wenn Vektoren berechnet wurden)
    ranked = vision.apply_visual(ranked, pins_list, department,
                                 vision.EmbeddingStore.load_existing())
    return {
        "profile": profile.to_dict(),
        "sources": products.source_names(),  # z.B. ["ebay", "etsy"] oder ["demo"]
        # 👍/👎 einrechnen: Dislikes raus, Ähnliches zu Likes nach oben
        "products": feedback.apply_feedback(ranked, all_products, feedback.load_feedback()),
    }


# --- Malis Vibe-Check -------------------------------------------------------------------

@app.get("/api/vibe")
def get_vibe(avoid: str | None = Query(None, max_length=300)):
    """Welchen Vibe gibt dein Pinterest ab? Immer positiv. avoid = letzter Spruch (kommt nicht nochmal)."""
    return vibe.vibe_check(storage.load_pins()["pins"], avoid=avoid)


# --- 👍 / 👎 Feedback -------------------------------------------------------------------

class Vote(BaseModel):
    """{"product_id": "prod-001", "vote": "like"}  –  vote: null löscht die Bewertung"""
    product_id: str
    vote: Literal["like", "dislike"] | None


@app.post("/api/feedback")
def post_feedback(vote: Vote):
    known_ids = {p.id for p in products.get_product_source().load()}
    if vote.product_id not in known_ids:
        raise HTTPException(404, "Produkt nicht gefunden.")
    feedback.set_vote(vote.product_id, vote.vote)
    return {"product_id": vote.product_id, "vote": vote.vote}


@app.get("/api/feedback")
def get_feedback():
    return feedback.load_feedback()


@app.get("/api/saved")
def get_saved(department: products.Department | None = None):
    """Die Merkliste: alle mit ♡ gemerkten Produkte, zuletzt gemerkte zuerst."""
    votes = feedback.load_feedback()
    liked = {pid: entry["at"] for pid, entry in votes.items() if entry["vote"] == "like"}
    saved = [
        {**p.model_dump(), "saved_at": liked[p.id], "vote": "like"}
        for p in products.get_product_source().load()
        if p.id in liked and (department is None or p.department == department)
    ]
    saved.sort(key=lambda item: item["saved_at"], reverse=True)
    return saved


@app.delete("/api/feedback")
def delete_feedback():
    """Alle Bewertungen zurücksetzen."""
    feedback.clear_feedback()
    return {"ok": True}


# --- Startseite ----------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def start_page():
    """Wer schon mit Pinterest verbunden ist, landet direkt im Shop – alle anderen auf
    der Startseite. (Die Startseite bleibt unter /index.html erreichbar.)"""
    if storage.load_tokens():
        return RedirectResponse("/shop.html")
    return FileResponse(FRONTEND_DIR / "index.html")


# Das Frontend (HTML/CSS/JS) wird direkt vom Backend ausgeliefert.
# Muss als LETZTES kommen, sonst würde es die API-Routen überdecken.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
