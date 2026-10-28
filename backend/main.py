"""Einstiegspunkt der FastAPI-App.

Starten mit:  uvicorn backend.main:app --reload
"""

import asyncio
import os
import secrets
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from backend import (analysis, currency, feedback, i18n, looks, matching, photo, pins, pinterest,
                     product_checks, products, quality, rate_limit, region,
                     shop_links, shops, similar, skimlinks, stats, storage, style_guide, vibe,
                     vibe_pages, vision)
from backend.config import FRONTEND_DIR, ConfigError

app = FastAPI(title="Malipin")

# Session-Cookie: merkt sich den OAuth-"state" zwischen Login und Callback.
# Das Cookie wird mit SESSION_SECRET signiert, damit niemand es fälschen kann.
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    print("WARNUNG: SESSION_SECRET fehlt in .env – nutze einen zufälligen Wert für diesen Start.")
    session_secret = secrets.token_hex(32)


class UserMiddleware:
    """Wessen Daten? Mit MULTI_USER=1 bekommt jede Person beim ersten Besuch eine zufällige,
    anonyme Kennung im (signierten) Session-Cookie – ohne Anmeldung, ohne Passwort. Alle
    Daten (Pinterest-Zugang, Pins, Merkliste …) liegen dann getrennt pro Kennung (storage.py).
    Ohne MULTI_USER (lokal) ist es immer dieselbe Person "local"."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not multi_user():
            await self.app(scope, receive, send)
            return
        session = scope["session"]
        if not session.get("uid"):
            session["uid"] = "u-" + secrets.token_urlsafe(16)
        token = storage.set_user(session["uid"])
        try:
            await self.app(scope, receive, send)
        finally:
            storage.reset_user(token)


def multi_user() -> bool:
    return os.getenv("MULTI_USER", "").strip() == "1"


# Reihenfolge: die Session (äußere Schicht) muss da sein, bevor UserMiddleware sie liest
app.add_middleware(UserMiddleware)
app.add_middleware(i18n.LanguageMiddleware)   # Sprache pro Anfrage (Cookie "lang" / Browser)
app.add_middleware(region.RegionMiddleware)   # Land & Währung pro Anfrage (Cookie "country" …)
# Auf dem Server (PUBLIC_URL=https://…): Sitzungs-Cookie nur über HTTPS
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax",
                   max_age=365 * 24 * 3600,  # Kennung bleibt ein Jahr (sonst Daten "weg")
                   https_only=os.getenv("PUBLIC_URL", "").startswith("https://"))


# --- Fehlerbehandlung -------------------------------------------------------------

# Fehlermeldungen in der Sprache der Person (Wörterbuch frontend/i18n/en.json)
@app.exception_handler(pinterest.NotConnectedError)
def not_connected(request: Request, exc: pinterest.NotConnectedError):
    return JSONResponse(status_code=401, content={"detail": i18n.tr(str(exc))})


@app.exception_handler(products.ProductSourceError)
def products_broken(request: Request, exc: products.ProductSourceError):
    return JSONResponse(status_code=500, content={"detail": i18n.tr(str(exc))})


@app.exception_handler(ConfigError)
def config_missing(request: Request, exc: ConfigError):
    return JSONResponse(status_code=500, content={"detail": i18n.tr(str(exc))})


@app.exception_handler(StarletteHTTPException)
def http_error(request: Request, exc: StarletteHTTPException):
    detail = i18n.tr(exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail},
                        headers=getattr(exc, "headers", None))


def local(items: list[dict]) -> list[dict]:
    """Für die Anzeige vorbereiten: Preise in der Währung der Person (local_price/local_currency,
    + converted, wenn umgerechnet; der Originalpreis bleibt in price/currency – im Shop zählt er)
    und Shop-Links ohne eigenes Partnerprogramm über Skimlinks (skimlinks.py)."""
    target, table = region.current().currency, currency.rates()
    for item in items:
        if item.get("price") is None or not item.get("currency"):
            continue
        converted = currency.convert(item["price"], item["currency"], target, table)
        if converted is not None:
            item.update(local_price=converted, local_currency=target,
                        converted=item["currency"] != target)
            if item.get("original_price"):        # Sale: "statt 49,90 €"
                item["local_original_price"] = currency.convert(item["original_price"],
                                                                item["currency"], target, table)
    for item in items:                            # Shop-Links ohne Partnerprogramm -> Skimlinks
        skimlinks.apply(item)
    return items


@app.get("/api/region")
def get_region():
    """Land & Währung der Person + alle wählbaren Länder (für die Auswahl im Footer)."""
    here = region.current()
    english = i18n.current() == "en"
    return {"country": here.code, "currency": here.currency,
            "countries": [{"code": r.code, "currency": r.currency,
                           "name": r.name_en if english else r.name_de}
                          for r in region.REGIONS.values()]}


@app.get("/i18n-en.js", include_in_schema=False)
def english_dictionary():
    """Wörterbuch für den Browser (frontend/i18n.js) – kurz zwischenspeicherbar."""
    return Response(i18n.dictionary_script(), media_type="application/javascript",
                    headers={"Cache-Control": "public, max-age=300"})


# --- Allgemein ----------------------------------------------------------------------

@app.get("/health")
def health():
    """Kleiner Check, ob der Server läuft."""
    return {"status": "ok"}


# --- Login mit Pinterest (OAuth) -------------------------------------------------------

def pinterest_open(request: Request) -> bool:
    """Darf diese Person Pinterest verbinden? Solange Pinterest uns nur "Trial"-Zugang gibt,
    klappt der Login nur für eingetragene Testkonten -> öffentlich "Bald verfügbar"
    (PINTEREST_OPEN=0 in .env). Als Admin angemeldet geht es trotzdem (zum Testen)."""
    return os.getenv("PINTEREST_OPEN", "1").strip() != "0" or bool(request.session.get("admin"))


@app.get("/api/features")
def features(request: Request):
    """Was ist für diese Person freigeschaltet? (Frontend: nav.js)"""
    return {"pinterest": pinterest_open(request)}


@app.get("/auth/login")
def login(request: Request):
    """Schickt den Nutzer zum Einloggen zu Pinterest."""
    if not pinterest_open(request):
        return RedirectResponse("/konto.html?bald=1")
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
        raise HTTPException(400, "Da ist beim Login etwas schiefgelaufen. Bitte starte ihn neu.")
    if not code:
        raise HTTPException(400, "Kein Code von Pinterest erhalten.")

    pinterest.exchange_code(code)
    if multi_user():
        link_pinterest_account(request)
    # Nach dem Login direkt zur Board-Auswahl
    return RedirectResponse("/konto.html")


def link_pinterest_account(request: Request) -> None:
    """Wiedererkennen über Pinterest: Dieselbe Person bekommt auf jedem Gerät dieselben Daten.
    Was sie vorher anonym gemacht hat (z.B. Merkliste), wird zum Pinterest-Konto übernommen."""
    account = pinterest.get_user_account()
    account_id = str(account.get("id") or account.get("username") or "")
    if not account_id:
        return
    linked = storage.linked_user_id(account_id)
    storage.merge_user_data(storage.current_user(), linked)
    request.session["uid"] = linked


def fresh_anonymous_session(request: Request) -> None:
    """Neue, leere Kennung für diesen Browser – z.B. nach "Verbindung trennen" auf einem
    geteilten Gerät sieht die nächste Person nichts mehr."""
    if multi_user():
        request.session["uid"] = "u-" + secrets.token_urlsafe(16)


@app.post("/auth/logout")
def logout(request: Request):
    """Trennt die Verbindung: Pinterest-Zugang löschen. Mit mehreren Personen bekommt der
    Browser danach eine neue, leere Kennung (die Daten bleiben beim Pinterest-Konto und sind
    beim nächsten Login wieder da)."""
    storage.delete_tokens()
    fresh_anonymous_session(request)
    return {"ok": True}


@app.delete("/api/me")
def delete_my_data(request: Request):
    """"Alle meine Daten löschen" (DSGVO): Pinterest-Zugang, Pins, Merkliste, Bewertungen,
    Analyse und Such-Zwischenspeicher der aktuellen Person – endgültig."""
    removed = storage.delete_user_data()
    analysis.forget_user()
    fresh_anonymous_session(request)
    return {"ok": True, "removed": removed}


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


# --- Admin: geprüfte Shops (nur mit ADMIN_PASSWORD in .env) --------------------------------

def admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "").strip()


def require_admin(request: Request) -> None:
    if not admin_password():
        raise HTTPException(404, "Nicht gefunden.")          # Admin ganz abgeschaltet
    if not request.session.get("admin"):
        raise HTTPException(401, "Bitte als Admin anmelden.")


class AdminLogin(BaseModel):
    password: str = Field(max_length=200)


@app.post("/api/admin/login")
def admin_login(data: AdminLogin, request: Request):
    if not admin_password():
        raise HTTPException(404, "Nicht gefunden.")
    if not secrets.compare_digest(data.password.encode(), admin_password().encode()):
        time.sleep(1)                                         # Raten bremsen
        raise HTTPException(401, "Falsches Passwort.")
    request.session["admin"] = True
    return {"ok": True}


@app.post("/api/admin/logout")
def admin_logout(request: Request):
    request.session.pop("admin", None)
    return {"ok": True}


@app.get("/api/admin/shops")
def admin_list_shops(request: Request):
    require_admin(request)
    return shops.load()


class Hit(BaseModel):
    type: Literal["view", "click"]
    page: str = Field("", max_length=100)
    url: str = Field("", max_length=2000)


@app.post("/api/hit", status_code=204)
def hit(data: Hit, request: Request):
    """Besucherzählung ohne Cookies (backend/stats.py): Seite aufgerufen / zu einem Shop geklickt."""
    stats.record(data.type, ip=request.client.host if request.client else "",
                 user_agent=request.headers.get("user-agent", ""),
                 page=data.page, shop=stats.shop_name(data.url))


@app.get("/api/admin/stats")
def admin_stats(request: Request, days: int = Query(30, ge=1, le=400)):
    require_admin(request)
    return stats.summary(days)


@app.get("/api/admin/feeds")
def admin_list_feeds(request: Request):
    """Feed-Namen für die Plattform-Auswahl auf der Admin-Seite."""
    from backend import feeds
    require_admin(request)
    try:
        return [{"name": f["name"], "label": f.get("label", f["name"])} for f in feeds.known_feeds()]
    except (feeds.FeedError, ValueError):
        return []


@app.post("/api/admin/shops")
def admin_add_shop(data: shops.ShopInput, request: Request):
    require_admin(request)
    try:
        return shops.add(data)
    except ValueError as err:
        raise HTTPException(400, str(err))


@app.delete("/api/admin/shops/{shop_id}")
def admin_delete_shop(shop_id: str, request: Request):
    require_admin(request)
    if not shops.remove(shop_id):
        raise HTTPException(404, "Shop nicht gefunden.")
    return {"ok": True}


PHOTO_SLOTS = asyncio.Semaphore(2)


@app.post("/api/photo")
async def upload_photo(request: Request, force: bool = False):
    """Foto hochladen → ähnliche Teile. Das Bild kommt als Rohdaten (z.B. image/jpeg),
    wird nur im Arbeitsspeicher analysiert und NICHT gespeichert."""
    if not request.headers.get("content-type", "").startswith("image/"):
        raise HTTPException(415, "Bitte ein Foto schicken (JPG, PNG, WebP …).")
    if not rate_limit.allow(request.client.host if request.client else "?"):
        raise HTTPException(429, "Das waren gerade sehr viele Fotos. Probier es in ein paar Minuten nochmal.")
    stats.record("photo", user_agent=request.headers.get("user-agent", ""))
    async with PHOTO_SLOTS:   # höchstens 2 Fotos gleichzeitig, der Rest wartet kurz
        return await analyse_photo(request, force)


async def analyse_photo(request: Request, force: bool) -> dict:
    data = await request.body()
    try:
        # Rechnen im Hintergrund-Thread, damit die App währenddessen erreichbar bleibt
        result = await run_in_threadpool(photo.recommend, data, force)
        local(result.get("products", []))
        return result
    except photo.PhotoError as err:
        raise HTTPException(400, str(err))
    except vision.VisionUnavailable:
        raise HTTPException(503, "Die Bilderkennung ist hier nicht installiert "
                                 "(pip install -r requirements-ai.txt).")


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
    return local(shop_links.filter_by_budget(items, max_price, region.current().currency))


# --- Produkte (Schritt 4) -------------------------------------------------------------

@app.get("/api/products")
def get_products(min_price: float | None = None, max_price: float | None = None,
                 category: str | None = None,
                 department: products.Department | None = None):
    """Produkte, optional gefiltert. Beispiel: /api/products?max_price=30&department=wohnen"""
    all_products = products.get_product_source().load()
    here = region.current()
    found = products.filter_products(all_products, min_price, max_price, category, department,
                                     currency=here.currency, country=here.code)
    return local([p.model_dump() for p in found])


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
        "product": local([detail])[0],
        "has_profile": profile.pin_count > 0,
        "similar": local(similar_items),
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
                        department: products.Department = "mode", trusted_only: bool = False,
                        gender: Literal["auto", "damen", "herren", "alle"] = "auto",
                        explain: bool = False):
    """Produkte einer Welt im Budget, sortiert nach Passung zum Stilprofil dieser Welt.
    gender: "auto" = wie deine Pins (pinnst du Damenmode, keine Herrenteile)."""
    pins_list = storage.load_pins()["pins"]
    profile = matching.build_style_profile(pins_list, department)
    if not pins_list:
        # Weder Pins noch Stil bekannt: keine Zufallsware zeigen (und nichts bei eBay suchen).
        # Nur, was die eigene Foto-Suche gefunden hat – sonst Einladung im Shop (needs_input).
        return guest_recommendations(profile, department, min_price, max_price, category)
    source = products.get_product_source()
    all_products = source.load()
    here = region.current()   # Budget in der eigenen Währung, nur Lieferbares
    selection = products.filter_products(all_products, min_price, max_price, category,
                                         department, currency=here.currency, country=here.code)
    if trusted_only:
        selection = [p for p in selection if p.trusted]
    # Bild-Prüfung (product_checks.py): KI-Bilder raus, Damen/Herren auch aus dem Bild
    selection = [p if p.gender or not product_checks.image_gender(p.id)
                 else p.model_copy(update={"gender": product_checks.image_gender(p.id)})
                 for p in selection if not product_checks.is_ai(p.id)]
    # Luxusmarken nur, wenn du sie pinnst (keine Gucci-Schuhe, wenn du nie Gucci gepinnt hast)
    pinned_luxury = set().union(*(quality.luxury_in(matching.pin_text(pin)) for pin in pins_list))
    selection = [p for p in selection
                 if not (lux := quality.luxury_in(p.name)) or lux & pinned_luxury]
    vision.embed_in_background(selection)   # neue Fotos still anschauen (fürs nächste Laden)
    wanted = for_whom(gender, pins_list) if department == "mode" else None
    selection = [p for p in selection if not (wanted and p.gender and p.gender != wanted)]
    ranked = shops.apply_bonus(matching.rank_products(selection, profile))
    for r in ranked:   # eBay ist unsere Hauptquelle -> bei ähnlicher Passung zuerst
        r["score"] = round(r["score"] + SOURCE_BONUS.get(r["id"].split("-", 1)[0], 0), 3)
    if wanted:   # sicher Damen- bzw. Herrenteile vor denen ohne Angabe
        for r in ranked:
            r["score"] = round(r["score"] + GENDER_BONUS * (r.get("gender") == wanted), 3)
    ranked.sort(key=lambda r: (-r["score"], r["price"]))
    # Bilder: "sieht aus wie deine Pins" (nur wenn Vektoren berechnet wurden)
    ranked = vision.apply_visual(ranked, pins_list, department,
                                 vision.EmbeddingStore.load_existing())
    # Nur, was wirklich zu den Pins passt – Rest gar nicht zeigen
    why = []
    if has_taste(profile):
        checked = product_checks.load()
        # Qualität vor Menge: lieber eine halbleere Seite als Unpassendes
        verdicts = [(r, *fit_check(r, profile, wanted, checked)) for r in ranked]
        fitting = [r for r, ok, _ in verdicts if ok]
        why = [{"name": r["name"], "shop": r["shop"], "shown": ok, "reason": reason}
               for r, ok, reason in verdicts]
    else:
        fitting = ranked
    # Fotos, die Mali gerade noch anschaut (Hintergrund) -> ehrlicher Hinweis im Shop
    pending_photos = sum(1 for r in ranked if "visual" in r and r["visual"] is None)
    unfitting, ranked = len(ranked) - len(fitting), fitting
    return {
        "profile": profile.to_dict(),
        "sources": products.source_names(),  # z.B. ["ebay", "etsy"] oder ["demo"]
        # Ausgefallene Quellen (z.B. eBay-Keys noch gesperrt) -> Hinweis im Shop statt still leer
        "warnings": source.warnings(),
        # 👍/👎 einrechnen: Dislikes raus, Ähnliches zu Likes nach oben
        # Danach Shops mischen, damit nicht ein großer Shop alles füllt
        "products": local(shops.mix(feedback.apply_feedback(ranked, all_products,
                                                             feedback.load_feedback()))),
        "currency": here.currency,
        "gender": wanted,
        "unfitting": unfitting,        # so viele ausgeblendet, weil sie nicht passen
        "pending_photos": pending_photos,
        **({"why": why} if explain else {}),
    }


@app.get("/api/why", response_class=PlainTextResponse)
def why_shown(department: products.Department = "mode"):
    """Zum Nachschauen im Browser: Warum ist welches Teil im Shop – oder nicht?
    http://localhost:8000/api/why  (bzw. ?department=wohnen)"""
    data = get_recommendations(department=department, explain=True)
    rows = data.get("why") or []
    shown = [r for r in rows if r["shown"]]
    lines = [f"{len(shown)} von {len(rows)} Teilen werden gezeigt.\n", "GEZEIGT:"]
    lines += [f"  ✓ {r['name'][:60]:<60} {r['shop'][:18]:<18} {r['reason']}" for r in shown]
    lines += ["", "AUSGEBLENDET (die ersten 80):"]
    lines += [f"  ✗ {r['name'][:60]:<60} {r['shop'][:18]:<18} {r['reason']}"
              for r in rows if not r["shown"]][:80]
    return "\n".join(lines)


def guest_recommendations(profile, department, min_price, max_price, category) -> dict:
    """Ohne Pins: nur Treffer der eigenen Foto-Suche (products.PhotoResultsSource)."""
    here = region.current()
    found = products.PhotoResultsSource().load() if storage.exists(products.PHOTO_RESULTS_FILE) else []
    found = products.filter_products(found, min_price, max_price, category, department,
                                     currency=here.currency, country=here.code)
    ranked = [{**p.model_dump(), "score": 0, "matched": [], "reason": ""} for p in found]
    return {"profile": profile.to_dict(), "sources": ["photo"] if found else [], "warnings": [],
            "products": local(ranked), "currency": here.currency, "gender": None, "unfitting": 0,
            "pending_photos": 0, "needs_input": not found}


def has_taste(profile: matching.StyleProfile) -> bool:
    """Wissen wir genug über den Stil? (Pins mit erkennbaren Teilen, Farben oder Stilen)"""
    return bool(profile.categories or profile.colors or profile.styles)


def fit_check(item: dict, profile: matching.StyleProfile, wanted: str | None = None,
              checked: dict | None = None) -> tuple[bool, str]:
    """Passt das Teil WIRKLICH zu den Pins? -> (ja/nein, Grund). Qualität vor Menge:
    1. Widerspruch zu den Pins (Skinny statt Baggy, Shorts statt Jeans) -> nie
    2. Die Art von Teil muss in den Pins deutlich vorkommen (nicht nur in einem von 50 Pins)
    3. Bilderkennung aktiv: Foto muss angeschaut sein und den Pins ähneln (VISUAL_GATE);
       "sieht aus wie deine Pins" reicht dann, sonst zusätzlich ein typisches Merkmal
    4. Ohne Bilderkennung: mindestens zwei typische Merkmale (Farbe, Stil, Schnitt, Marke)
    5. Pins zeigen Damen- bzw. Herrenmode, Teil laut Bild unklar -> nein
    Typisch = kommt in mind. 10 % der Pins vor (eine Farbe aus einem einzigen Pin zählt nicht)."""
    if item.get("clashes"):
        return False, "Widerspruch zu den Pins: " + ", ".join(item["clashes"])
    category = item["category"]
    if profile.categories and profile.categories[category] < category_minimum(profile):
        return False, f"{category} kommt in deinen Pins kaum vor"
    matched = item.get("matched") or []
    features = [m for m in matched if m != category and typical(m, category, profile)]
    if wanted and not item.get("gender") and item["id"] in (checked or {}):
        return False, "unklar, ob Damen oder Herren"
    if "visual" in item:               # Bilderkennung aktiv (Pins haben Bild-Vektoren)
        if item["visual"] is None:     # Foto noch nicht geprüft -> nur ganz sichere Text-Treffer
            if category in matched and len(features) >= 2:
                return True, "noch ohne Fotoprüfung, aber " + ", ".join(features)
            return False, "Foto noch nicht angeschaut"
        if item["visual"] < VISUAL_GATE:
            return False, f"Foto sieht anders aus als deine Pins ({item['visual']:.2f})"
        if item.get("looks_like_pins") and (category in matched or not profile.categories):
            return True, "sieht aus wie deine Pins"
        if category in matched and features:
            return True, "Foto passt + " + ", ".join(features)
        return False, "Foto ähnlich, aber kein typisches Merkmal"
    if (category in matched or not profile.categories) and len(features) >= 2:
        return True, ", ".join(features)
    return False, "zu wenig typische Merkmale" + (f" (nur {', '.join(features)})" if features else "")


def fits_pins(item: dict, profile: matching.StyleProfile, wanted: str | None = None,
              checked: dict | None = None) -> bool:
    return fit_check(item, profile, wanted, checked)[0]


TYPICAL_SHARE = 0.10        # Merkmal zählt ab 10 % der Pins
DETAIL_TYPICAL_SHARE = 0.25  # Schnitt/Detail: ab 25 % der Pins dieser Art (z.B. 1 von 4 Jeans-Pins)


def category_minimum(profile: matching.StyleProfile) -> int:
    """Wie oft muss eine Art von Teil in den Pins vorkommen? Wenige Pins: 1, sonst 2 bzw. 10 %."""
    if profile.pin_count < 5:
        return 1
    return max(2, round(profile.pin_count * TYPICAL_SHARE))


def typical(term: str, category: str, profile: matching.StyleProfile) -> bool:
    """Ist das Merkmal typisch für die Pins – oder nur ein Zufall aus einem einzelnen Pin?"""
    if profile.detail_share(category, term) >= DETAIL_TYPICAL_SHARE:
        return True
    return profile.weight(term) >= TYPICAL_SHARE or (profile.pin_count < 5 and profile.mentions(term) > 0)


GENDER_BONUS = 0.3   # wie ein Begriff in knapp jedem dritten Pin
# Mindest-Ähnlichkeit des Fotos zu den Pins (0..1, "sieht aus wie" ab 0.6) – darunter nie
VISUAL_GATE = 0.25   # Produktfotos (flach/Bügel) ähneln Outfit-Pins nie stark: gute Treffer 0.25-0.45
SOURCE_BONUS = {"ebay": 0.2, "etsy": -0.1}   # Vorrang für eBay, Etsy etwas zurück


def for_whom(choice: str, pins_list: list[dict]) -> str | None:
    """Damen/Herren: bewusste Wahl im Shop – sonst aus den Pins erkannt (None = alles)."""
    if choice in ("damen", "herren"):
        return choice
    return matching.pins_gender(pins_list) if choice == "auto" else None


@app.get("/api/looks")
def get_looks():
    """Shop the Look: Outfit-Pins mit den passenden Teilen (looks.py) – im Budget egal,
    Lieferland zählt."""
    here = region.current()
    available = products.filter_products(products.get_product_source().load(),
                                         department="mode", country=here.code)
    disliked = feedback.ids_with_vote(feedback.load_feedback(), "dislike")
    pins_list = storage.load_pins()["pins"]
    wanted = for_whom("auto", pins_list)
    found = looks.shop_the_look(pins_list,
                                [p for p in available if p.id not in disliked
                                 and not (wanted and p.gender and p.gender != wanted)],
                                vision.EmbeddingStore.load_existing())
    for look in found:
        local(look["items"])
    return found


# --- Malis Vibe-Check -------------------------------------------------------------------

@app.get("/api/styles")
def get_styles():
    """Stil-Lexikon: alle Vibes und Stil-Begriffe mit Erklärung (style_guide.py)."""
    return style_guide.guide()


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
    return local(saved)


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


# --- Impressum & Datenschutz (gleiche Seiten wie auf der Vorstellungsseite) ----------------

@app.get("/impressum.html", response_class=HTMLResponse)
def impressum():
    from scripts import build_site
    try:
        return build_site.impressum_page()
    except build_site.BuildError as error:          # website/impressum.json fehlt/unvollständig
        raise HTTPException(503, str(error)) from error


@app.get("/datenschutz.html", response_class=HTMLResponse)
@app.get("/privacy.html", response_class=HTMLResponse)     # englische Adresse, gleiche Seite
def datenschutz():
    from scripts import build_site
    privacy = build_site.markdown_to_html((build_site.ROOT / "PRIVACY.md").read_text("utf-8"))
    return build_site.subpage("Privacy Policy", privacy, "How Malipin handles your data.",
                              "/datenschutz.html", lang="en")


# --- Eine Seite pro Vibe (/stil/goth-baddie) + Sitemap für Google ----------------------------

@app.get("/stil/{name}", response_class=HTMLResponse)
def vibe_page(name: str):
    page = vibe_pages.render(name)
    if page is None:
        raise HTTPException(404, "Diesen Vibe kenne ich nicht.")
    return page


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    paths = ["/", "/foto.html", "/stile.html", *vibe_pages.all_paths()]
    urls = "".join(f"  <url><loc>{vibe_pages.SITE_URL}{p}</loc></url>\n" for p in paths)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    return Response(xml, media_type="application/xml")


# Das Frontend (HTML/CSS/JS) wird direkt vom Backend ausgeliefert.
# Muss als LETZTES kommen, sonst würde es die API-Routen überdecken.
class FrontendFiles(StaticFiles):
    """Wie StaticFiles – aber der Browser fragt immer kurz nach, ob sich eine Datei geändert hat
    (no-cache + ETag). Sonst sieht man nach einem Update manchmal noch das alte Design."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
