"""Besucherzahlen ohne Cookies und ohne Tracking: nur Summen pro Tag.

Gezählt werden Seitenaufrufe, Besucher, Klicks zu Shops und Foto-Suchen. Für "Besucher" wird
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


def record(kind: str, *, ip: str = "", user_agent: str = "", page: str = "", shop: str = "") -> None:
    """kind: "view" (Seite), "click" (zu einem Shop) oder "photo" (Foto-Suche)."""
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
    for d in recent:
        for shop, count in d["shops"].items():
            shops[shop] = shops.get(shop, 0) + count
    return {"days": recent, "totals": totals,
            "top_shops": sorted(shops.items(), key=lambda item: -item[1])[:10]}
