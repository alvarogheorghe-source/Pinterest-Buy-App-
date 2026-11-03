"""Second Hand bei Vinted, willhaben und Depop suchen – als einfache Such-Links.

Beide haben weder eine öffentliche Schnittstelle noch ein Partnerprogramm, und Inserate
auszulesen (Scraping) erlauben sie nicht. Darum zeigt Mali nur Knöpfe, die dort die Suche
mit den erkannten Begriffen öffnen ("schwarz Jeans herren"). Kein Partnerlink, keine
Provision -> auch keine "Werbung"-Kennzeichnung.

Nur in Ländern, in denen es die Plattform gibt. Vinted/willhaben suchen mit den deutschen
Begriffen (AT/DE). Depop ist englischsprachig und weltweit: dort werden die Begriffe ins
Englische übersetzt ("schwarz Hosen" -> "black pants").
"""

from urllib.parse import quote_plus

from backend import i18n, region

# Plattform -> {Land: Such-Adresse mit {q}}
SITES = {
    "Vinted": {"AT": "https://www.vinted.at/catalog?search_text={q}",
               "DE": "https://www.vinted.de/catalog?search_text={q}"},
    "willhaben": {"AT": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword={q}"},
    "Depop": {code: "https://www.depop.com/search/?q={q}"
              for code in ("AT", "DE", "CH", "GB", "IE", "US", "CA", "AU")},
}
ENGLISH_SITES = {"Depop"}       # Suchbegriffe dort auf Englisch


def _english(term: str) -> str:
    """Begriff ins Englische, wenn das Wörterbuch ihn kennt (auch klein/groß geschrieben)."""
    for variant in (term, term.capitalize(), term.lower()):
        translated = i18n.tr(variant, "en")
        if translated != variant:
            return translated
    return term


def sites() -> list[str]:
    """Welche Plattformen gibt es im Land der Person?"""
    return [name for name, urls in SITES.items() if region.current().code in urls]


def search_url(site: str, terms: list[str]) -> str | None:
    clean = [t.strip() for t in terms if t and t.strip()]
    if site in ENGLISH_SITES:
        clean = [_english(t) for t in clean]
    words = " ".join(dict.fromkeys(t.lower() for t in clean))
    url = SITES.get(site, {}).get(region.current().code)
    return url.format(q=quote_plus(words)) if url and words else None


def links(terms: list[str]) -> list[dict]:
    """[{"name": "Vinted", "url": ...}, ...] für das Land der Person (leer, wenn keine passt)."""
    return [{"name": name, "url": url} for name in sites()
            if (url := search_url(name, terms))]
