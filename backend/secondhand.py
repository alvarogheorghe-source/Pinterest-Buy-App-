"""Second Hand bei Vinted und willhaben suchen – als einfache Such-Links.

Beide haben weder eine öffentliche Schnittstelle noch ein Partnerprogramm, und Inserate
auszulesen (Scraping) erlauben sie nicht. Darum zeigt Mali nur Knöpfe, die dort die Suche
mit den erkannten Begriffen öffnen ("schwarz Jeans herren"). Kein Partnerlink, keine
Provision -> auch keine "Werbung"-Kennzeichnung.

Nur in Ländern, in denen es die Plattform gibt (Begriffe sind deutsch -> nur AT/DE).
"""

from urllib.parse import quote_plus

from backend import region

# Plattform -> {Land: Such-Adresse mit {q}}
SITES = {
    "Vinted": {"AT": "https://www.vinted.at/catalog?search_text={q}",
               "DE": "https://www.vinted.de/catalog?search_text={q}"},
    "willhaben": {"AT": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword={q}"},
}


def sites() -> list[str]:
    """Welche Plattformen gibt es im Land der Person?"""
    return [name for name, urls in SITES.items() if region.current().code in urls]


def search_url(site: str, terms: list[str]) -> str | None:
    words = " ".join(dict.fromkeys(t.strip().lower() for t in terms if t and t.strip()))
    url = SITES.get(site, {}).get(region.current().code)
    return url.format(q=quote_plus(words)) if url and words else None


def links(terms: list[str]) -> list[dict]:
    """[{"name": "Vinted", "url": ...}, ...] für das Land der Person (leer, wenn keine passt)."""
    return [{"name": name, "url": url} for name in sites()
            if (url := search_url(name, terms))]
