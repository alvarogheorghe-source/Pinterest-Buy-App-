"""Land & Währung pro Person – damit Malipin weltweit funktioniert.

Die Region bestimmt:
- die Währung für Preise und Budget (umgerechnet mit currency.py)
- den eBay-Marktplatz und die Sprache der eBay-Suchen (ebay.com sucht englisch, ebay.at deutsch)
- wohin AliExpress liefern soll
- welche Produkt-Feeds passen ("countries" in feeds.json)

Welche Region? Cookie "country" (setzt frontend/i18n.js: gespeicherte Wahl oder Land aus der
Browsersprache, z.B. "en-US" -> US), sonst ein Länder-Header vom Hosting (z.B. Cloudflare
"CF-IPCountry"), sonst die Browsersprache, sonst DEFAULT_COUNTRY aus .env (Standard: AT).

Neues Land? Unten in REGIONS eintragen (eBay-Marktplatz-IDs: developer.ebay.com).
"""

import os
import re
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    code: str            # ISO-Ländercode, z.B. "AT"
    currency: str        # ISO-Währung, z.B. "EUR"
    ebay: str            # eBay-Marktplatz, z.B. "EBAY_AT"
    search_lang: str     # Sprache der Shop-Titel dort: "de" oder "en"
    name_de: str
    name_en: str


REGIONS = {r.code: r for r in [
    Region("AT", "EUR", "EBAY_AT", "de", "Österreich", "Austria"),
    Region("DE", "EUR", "EBAY_DE", "de", "Deutschland", "Germany"),
    Region("CH", "CHF", "EBAY_CH", "de", "Schweiz", "Switzerland"),
    Region("GB", "GBP", "EBAY_GB", "en", "Großbritannien", "United Kingdom"),
    Region("IE", "EUR", "EBAY_IE", "en", "Irland", "Ireland"),
    Region("US", "USD", "EBAY_US", "en", "USA", "United States"),
    Region("CA", "CAD", "EBAY_CA", "en", "Kanada", "Canada"),
    Region("AU", "AUD", "EBAY_AU", "en", "Australien", "Australia"),
]}


def default_code() -> str:
    code = os.getenv("DEFAULT_COUNTRY", "").strip().upper()
    return code if code in REGIONS else "AT"


_current: ContextVar[str | None] = ContextVar("region", default=None)


def current() -> Region:
    return REGIONS[_current.get() or default_code()]


def choose(cookie_header: str = "", geo_country: str = "", accept_language: str = "") -> str:
    """Ländercode aus Cookie, Hosting-Header oder Browsersprache – sonst Standard."""
    match = re.search(r"(?:^|;\s*)country=([A-Z]{2})", cookie_header or "")
    if match and match.group(1) in REGIONS:
        return match.group(1)
    if (geo_country or "").upper() in REGIONS:
        return geo_country.upper()
    for part in (accept_language or "").split(","):
        tag = part.split(";")[0].strip()
        if "-" in tag and tag.split("-")[1].upper() in REGIONS:
            return tag.split("-")[1].upper()
        if tag[:2].lower() == "en":
            return "US"
        if tag[:2].lower() == "de":
            return default_code() if REGIONS[default_code()].search_lang == "de" else "DE"
    return default_code()


class RegionMiddleware:
    """Merkt sich pro Anfrage die Region (reines ASGI, wie LanguageMiddleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        token = _current.set(choose(headers.get("cookie", ""), headers.get("cf-ipcountry", ""),
                                    headers.get("accept-language", "")))
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(token)


def use(code: str):
    """Für Tests und Hintergrund-Arbeit: Region festlegen. Gibt ein Token zum Zurücksetzen."""
    return _current.set(code)
