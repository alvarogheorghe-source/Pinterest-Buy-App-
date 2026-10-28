"""Skimlinks: Provision auch für Shops, mit denen wir kein eigenes Partnerprogramm haben.

Ohne Skript auf unserer Seite (das würde Tracking-Cookies setzen -> Cookie-Banner nötig):
Links zu Shops werden über Skimlinks' Weiterleitung geschickt
    https://go.skimresources.com/?id=<Kennung>&xs=1&url=<Shop-Adresse>
Gezählt wird erst dort, nach dem Klick. Malipin selbst setzt dafür kein Cookie.

Gilt nur für Links, die noch KEIN Partnerlink sind (Awin, eBay mit Kampagne, AliExpress …
bleiben, wie sie sind). Umgeleitete Links sind Werbung -> sponsored=True (Kennzeichnung).
Einschalten: SKIMLINKS_ID in .env (Skimlinks -> Publisher-ID, z.B. 123456X1234567).
"""

import os
import re
from urllib.parse import quote

WRAP = "https://go.skimresources.com/?id={id}&xs=1&url={url}"
# Schon ein Partnerlink (oder gar kein Shop) -> nicht anfassen
ALREADY = re.compile(r"awin1\.com|s\.click\.aliexpress|rover\.ebay|campid=|mkcid=|"
                     r"skimresources\.com|pinterest\.|pin\.it", re.I)


def publisher_id() -> str:
    return os.getenv("SKIMLINKS_ID", "").strip()


def wrap(url: str) -> str:
    return WRAP.format(id=publisher_id(), url=quote(url, safe=""))


def apply(item: dict) -> dict:
    """Shop-Links eines Produkts/Pin-Teils über Skimlinks leiten (wenn eingeschaltet)."""
    if not publisher_id() or item.get("sponsored"):
        return item
    for key in ("affiliate_url", "link"):
        url = item.get(key)
        if isinstance(url, str) and url.startswith(("https://", "http://")) and not ALREADY.search(url):
            item[key] = wrap(url)
            item["sponsored"] = True             # jetzt ein Partnerlink -> "Werbung"
    return item
