"""Besucherzahlen ohne Cookies und ohne Tracking: nur Summen pro Tag.

Gezählt werden Seitenaufrufe, Besucher, Klicks zu Shops, Foto-Suchen und woher die Besucher
kommen (Quelle: ?von=tiktok im Link, sonst die verweisende Seite, sonst die Instagram-/TikTok-App). Für "Besucher" wird
aus IP-Adresse + Browser + einem täglich neuen Zufallswert eine Prüfsumme gebildet, die nur im
Arbeitsspeicher liegt und um Mitternacht verfällt. Gespeichert werden nur die Zahlen
(data/stats.json), nie IP-Adressen oder Kennungen. Deshalb braucht es kein Cookie-Banner.
"""

import hashlib
import re
import secrets
import threading
import time
from urllib.parse import unquote

from backend import storage

STATS_FILE = "stats.json"
KEEP_DAYS = 400
PAGES = {"/", "/shop.html", "/stile.html", "/foto.html", "/produkt.html", "/merkliste.html",
         "/konto.html"}
BOTS = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse", re.I)

_lock = threading.Lock()
_today = {"day": "", "salt": "", "seen": set()}


# Verweisende Seite -> lesbare Quelle. Verglichen wird ein Teil des Namens (l.instagram.com,
# google.at), nicht irgendein Textstück – sonst wäre "reddit.com" wegen "t.co" plötzlich X.
SOURCES = {"instagram": "instagram", "tiktok": "tiktok", "pinterest": "pinterest",
           "google": "google", "facebook": "facebook", "fb": "facebook", "youtube": "youtube",
           "bing": "bing", "duckduckgo": "duckduckgo", "twitter": "x", "whatsapp": "whatsapp",
           "snapchat": "snapchat", "reddit": "reddit"}
EXACT_SOURCES = {"t.co": "x", "x.com": "x"}
# In-App-Browser schicken oft keine verweisende Seite mit, verraten sich aber im Browsernamen
APP_AGENTS = [(re.compile(r"Instagram", re.I), "instagram"),
              (re.compile(r"musical_ly|BytedanceWebview|TikTok", re.I), "tiktok"),
              (re.compile(r"Pinterest", re.I), "pinterest"),
              (re.compile(r"FBAN|FBAV", re.I), "facebook"),
              (re.compile(r"Snapchat", re.I), "snapchat")]


def source_of(tag: str = "", referrer: str = "", user_agent: str = "", own_host: str = "") -> str:
    """Woher kommt jemand? ?von=/utm_source gewinnt, dann die verweisende Seite, dann die App.
    Nur kurze, harmlose Namen (keine ganzen Adressen)."""
    tag = re.sub(r"[^a-z0-9_-]", "", (tag or "").lower())[:30]
    if tag:
        return tag
    match = re.match(r"https?://([^/:?#]+)", referrer or "")
    host = match.group(1).lower().removeprefix("www.") if match else ""
    if host and host != own_host.lower().removeprefix("www."):
        if host in EXACT_SOURCES:
            return EXACT_SOURCES[host]
        for label in host.split("."):
            if label in SOURCES:
                return SOURCES[label]
        return re.sub(r"[^a-z0-9.-]", "", host)[:40]
    for pattern, name in APP_AGENTS:
        if pattern.search(user_agent or ""):
            return name
    return "direkt"


def _day() -> str:
    return time.strftime("%Y-%m-%d")


def is_bot(user_agent: str) -> bool:
    return not user_agent or bool(BOTS.search(user_agent))


def _new_visitor(ip: str, user_agent: str) -> bool:
    day = _day()
    if _today["day"] != day:
        _today.update(day=day, salt=secrets.token_hex(16), seen=set())
    key = hashlib.sha256(f"{_today['salt']}|{ip}|{user_agent}".encode()).hexdigest()[:16]
    if key in _today["seen"]:
        return False
    _today["seen"].add(key)
    return True


def record(kind: str, *, ip: str = "", user_agent: str = "", page: str = "", shop: str = "",
           source: str = "") -> None:
    """kind: "view" (Seite), "click" (zu einem Shop) oder "photo" (Foto-Suche).
    source (bei "view"): woher (source_of) – gezählt nur beim ersten Aufruf am Tag."""
    if is_bot(user_agent):
        return
    with _lock:
        data = storage.read_json(STATS_FILE, default={})
        day = data.setdefault(_day(), {"views": 0, "visitors": 0, "clicks": 0, "photos": 0,
                                       "pages": {}, "shops": {}})
        if kind == "view":
            day["views"] += 1
            if page in PAGES:
                day["pages"][page] = day["pages"].get(page, 0) + 1
            if _new_visitor(ip, user_agent):
                day["visitors"] += 1
                if source:
                    sources = day.setdefault("sources", {})
                    sources[source] = sources.get(source, 0) + 1
        elif kind == "click":
            day["clicks"] += 1
            if shop:
                day["shops"][shop] = day["shops"].get(shop, 0) + 1
        elif kind == "photo":
            day["photos"] += 1
        for old in sorted(data)[:-KEEP_DAYS]:
            del data[old]
        storage.write_json(STATS_FILE, data)


def shop_name(url: str) -> str:
    """https://www.ebay.de/itm/123 -> ebay.de (nur der Shop, nicht das Produkt)."""
    wrapped = re.search(r"[?&]url=([^&]+)", url or "")
    if wrapped and "skimresources" in url:                # Skimlinks-Umleitung -> echter Shop
        url = unquote(wrapped.group(1))
    match = re.match(r"https?://(?:www\.)?([^/:?#]+)", url or "")
    return match.group(1).lower()[:60] if match else ""


def summary(days: int = 30) -> dict:
    """Letzte Tage + Summen für die Admin-Seite."""
    data = storage.read_json(STATS_FILE, default={})
    recent = [{"day": day, **data[day]} for day in sorted(data)[-days:]]
    totals = {key: sum(d[key] for d in recent) for key in ("views", "visitors", "clicks", "photos")}
    shops: dict[str, int] = {}
    sources: dict[str, int] = {}
    for d in recent:
        for shop, count in d["shops"].items():
            shops[shop] = shops.get(shop, 0) + count
        for source, count in d.get("sources", {}).items():
            sources[source] = sources.get(source, 0) + count
    return {"days": recent, "totals": totals,
            "top_shops": sorted(shops.items(), key=lambda item: -item[1])[:10],
            "sources": sorted(sources.items(), key=lambda item: -item[1])[:15]}
