"""SEO-Daten der Startseite: strukturierte Daten (JSON-LD) für Google & Co.

Die Häufigen Fragen stehen sichtbar auf der Startseite (<details>). Google will, dass die
FAQ-Daten GENAU dem sichtbaren Text entsprechen – darum werden sie hier aus der Seite
erzeugt statt von Hand gepflegt. Nach jeder Änderung an Fragen oder Texten:

    python -m scripts.seo

(tests/test_seo.py meldet, wenn das vergessen wurde.)
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "frontend" / "index.html"
SITE_URL = "https://malipin.com/"
START, END = "<!-- seo:jsonld", "<!-- /seo:jsonld -->"


def _text(fragment: str) -> str:
    """HTML-Schnipsel -> reiner Text ("Was zählt zu „Wohnen &amp; Deko“?" -> "… & …")."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def faq(page: str) -> list[tuple[str, str]]:
    """[(Frage, Antwort), …] aus den <details> der Seite."""
    return [(_text(q), _text(a)) for q, a in re.findall(
        r"<details>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>", page, re.DOTALL)]


def meta(page: str, name: str) -> str:
    match = re.search(rf'<meta name="{name}" content="([^"]*)"', page)
    return html.unescape(match.group(1)) if match else ""


def jsonld(page: str) -> dict:
    org = SITE_URL + "#organisation"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "@id": org, "name": "Malipin", "url": SITE_URL,
             "logo": SITE_URL + "img/icon-512.png"},
            {"@type": "WebSite", "@id": SITE_URL + "#website", "name": "Malipin", "url": SITE_URL,
             "inLanguage": "de", "publisher": {"@id": org}},
            {"@type": "WebApplication", "name": "Malipin", "url": SITE_URL,
             "description": meta(page, "description"), "inLanguage": "de",
             "applicationCategory": "LifestyleApplication", "operatingSystem": "Web",
             "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
             "publisher": {"@id": org}},
            {"@type": "FAQPage", "@id": SITE_URL + "#faq",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in faq(page)]},
        ],
    }


def render(page: str) -> str:
    """Die Seite mit aktuellem JSON-LD-Block."""
    data = json.dumps(jsonld(page), ensure_ascii=False, indent=2).replace("</", "<\\/")
    block = (f"{START} – wird erzeugt mit: python -m scripts.seo (nicht von Hand ändern) -->\n"
             f'  <script type="application/ld+json">\n{data}\n  </script>\n  {END}')
    return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, page,
                  count=1, flags=re.DOTALL)


if __name__ == "__main__":
    INDEX.write_text(render(INDEX.read_text("utf-8")), "utf-8")
    print(f"JSON-LD aktualisiert ({len(faq(INDEX.read_text('utf-8')))} Fragen).")
