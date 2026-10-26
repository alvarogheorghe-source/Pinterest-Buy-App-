"""Sprache der App: Deutsch oder Englisch – ein Wörterbuch für Website, App und Server.

Das Wörterbuch frontend/i18n/en.json übersetzt deutsche Texte ins Englische ("deutscher
Text" -> "englischer Text", Platzhalter wie {n}). Deutsch ist die Quelle: Fehlt eine
Übersetzung, bleibt der deutsche Text stehen (und ein Test meldet es).

Welche Sprache? Das Cookie "lang" (setzt frontend/i18n.js: gespeicherte Wahl oder
Browsersprache), sonst der Accept-Language-Header des Browsers, sonst Deutsch.
LanguageMiddleware merkt sich die Sprache pro Anfrage; tr() übersetzt dann automatisch.
"""

import json
import re
from contextvars import ContextVar
from functools import lru_cache

from backend.config import BASE_DIR

DICTIONARY = BASE_DIR / "frontend" / "i18n" / "en.json"
LANGUAGES = ("de", "en")
DEFAULT = "de"

_current: ContextVar[str] = ContextVar("lang", default=DEFAULT)


@lru_cache(maxsize=1)
def dictionary() -> dict[str, str]:
    """Wörterbuch + Schnitt & Details aus details.py (dort steht das Englische schon drin)."""
    from backend import details
    words = {d.de: d.en[:1].upper() + d.en[1:] for d in details.DETAILS}
    return {**words, **json.loads(DICTIONARY.read_text("utf-8"))["texts"]}


def _norm(text: str) -> str:
    return " ".join(text.split())


def current() -> str:
    return _current.get()


def tr(text: str, lang: str | None = None, **values) -> str:
    """Deutschen Text in die aktuelle Sprache. tr("{n} Pins", n=3) -> "3 Pins"."""
    lang = lang or current()
    if lang == "en":
        text = dictionary().get(_norm(text), text)
    return text.format(**values) if values else text


def choose(cookie_header: str, accept_language: str) -> str:
    """Sprache aus Cookie "lang" oder Accept-Language ("en-GB,en;q=0.9,de;q=0.8")."""
    match = re.search(r"(?:^|;\s*)lang=([a-z]{2})", cookie_header or "")
    if match and match.group(1) in LANGUAGES:
        return match.group(1)
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code:
            return "de" if code == "de" else "en"   # alles außer Deutsch -> Englisch
    return DEFAULT


class LanguageMiddleware:
    """Merkt sich pro Anfrage die Sprache (reines ASGI, wie UserMiddleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        token = _current.set(choose(headers.get("cookie", ""), headers.get("accept-language", "")))
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(token)


def dictionary_script() -> str:
    """Das Wörterbuch für den Browser (geladen von jeder App-Seite vor i18n.js)."""
    data = json.dumps(dictionary(), ensure_ascii=False).replace("</", "<\\/")
    return f"window.MALIPIN_EN = {data};\n"
