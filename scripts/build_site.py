"""Baut die öffentliche Vorstellungsseite für malipin.com (statisch, für GitHub Pages).

Quelle ist die echte Startseite (frontend/index.html). Weil auf GitHub Pages kein Server
läuft, werden alle Buttons, die den Server brauchen ("Mit Pinterest verbinden", Shop,
Merkliste), zu "Bald verfügbar". Dazu kommen Datenschutz (aus PRIVACY.md) und Impressum
(aus website/impressum.json).

Starten:   python scripts/build_site.py
Ergebnis:  Ordner site/ – lokal ansehen mit:  python -m http.server -d site 8080
Online:    passiert automatisch bei jedem Push (.github/workflows/pages.yml)

Ohne ausgefülltes Impressum bricht das Skript ab – die Seite geht nie ohne Impressum online.
"""

import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT = ROOT / "site"
IMPRESSUM = ROOT / "website" / "impressum.json"

COPY = ["style.css", "landing.css", "bunny.css", "bunny.js", "site.webmanifest",
        "img/favicon.svg", "img/favicon-48.png", "img/apple-touch-icon.png",
        "img/icon-192.png", "img/icon-512.png", "img/og-image.png"]
SOON = "Bald verfügbar"
SITE_URL = "https://malipin.com"
# Seiten für Google (sitemap.xml) – 404 bewusst nicht
PAGES = ["/", "/datenschutz.html", "/impressum.html"]


class BuildError(Exception):
    pass


# --- Startseite: Server-Buttons -> "Bald verfügbar" ------------------------------------------

def static_index(source: str) -> str:
    page = source

    # Verbinden-Buttons (führen alle zu /konto.html) -> nicht klickbares "Bald verfügbar"
    page = re.sub(
        r'<a href="/konto\.html" class="button([^"]*)">.*?</a>',
        lambda m: f'<span class="button{m.group(1)} soon" aria-disabled="true">{SOON}</span>',
        page, flags=re.DOTALL)
    # Foto-Suche braucht den Server -> "Foto-Suche bald verfügbar"
    page = re.sub(
        r'<a href="/foto\.html" class="button([^"]*)">.*?</a>',
        lambda m: f'<span class="button{m.group(1)} soon" aria-disabled="true">Foto-Suche {SOON.lower()}</span>',
        page, flags=re.DOTALL)
    # "Shop ansehen", Shop/Merkliste im Kopf -> weg
    page = re.sub(r'\s*<a href="/shop\.html" class="button large outline">.*?</a>', "", page)
    page = re.sub(r'\s*<a href="/shop\.html" class="header-link">.*?</a>', "", page)
    page = re.sub(r'\s*<a href="/merkliste\.html"[^>]*>.*?</a>', "", page, flags=re.DOTALL)
    page = re.sub(r'\s*<a href="/foto\.html"[^>]*>.*?</a>', "", page, flags=re.DOTALL)
    # Welten-Karten: keine Links mehr, Pfeil-Text -> "Bald verfügbar"
    page = re.sub(r'<a href="/shop\.html#(mode|wohnen)" class="world', r'<a class="world', page)
    page = re.sub(r'<span class="world-link">.*?</span>\s*(?=</a>)',
                  f'<span class="world-link">{SOON}</span>\n      ', page, flags=re.DOTALL)
    # Footer-Links
    page = re.sub(r'<nav class="footer-links">.*?</nav>',
                  '<nav class="footer-links">\n        <a href="/datenschutz.html">Datenschutz</a>\n'
                  '        <a href="/impressum.html">Impressum</a>\n      </nav>',
                  page, flags=re.DOTALL)
    page = page.replace("<p>Prototyp mit Beispieldaten · Impressum folgt</p>",
                        "<p>Malipin startet bald.</p>")
    # Kein Server -> kein Merklisten-Zähler; Mali weiß, dass er auf der Vorstellungsseite ist
    page = page.replace('  <script src="nav.js" defer></script>\n', "")
    page = page.replace("<body", "<body data-static", 1)

    leftovers = re.findall(r'href="/(?:konto|shop|merkliste|produkt|foto)\.html|href="/auth/', page)
    if leftovers:
        raise BuildError(f"Noch Links zum Server in der Startseite: {leftovers}")
    return page


# --- Unterseiten (Datenschutz, Impressum) im Look der Website ---------------------------------

def logo() -> str:
    match = re.search(r"<!-- logo -->.*?<!-- /logo -->", (FRONTEND / "index.html").read_text("utf-8"),
                      re.DOTALL)
    return match.group(0)


def subpage(title: str, body: str, description: str = "", path: str | None = None,
            lang: str = "de") -> str:
    """Unterseite im Look der Website. path=None -> nicht in Google (z.B. 404)."""
    seo = (f'  <meta name="robots" content="index, follow">\n'
           f'  <link rel="canonical" href="{SITE_URL}{path}">\n' if path
           else '  <meta name="robots" content="noindex">\n')
    if description:
        seo += f'  <meta name="description" content="{html.escape(description)}">\n'
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} – Malipin</title>
{seo}  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/img/favicon-48.png" type="image/png" sizes="48x48">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
  <meta name="theme-color" content="#c93a69">
  <meta property="og:title" content="{html.escape(title)} – Malipin">
  <meta property="og:image" content="{SITE_URL}/img/og-image.png">
  <link rel="stylesheet" href="/style.css">
  <link rel="stylesheet" href="/bunny.css">
</head>
<body data-static>
  <header class="site-header">
    {logo()}
  </header>
  <main class="legal">
{body}
  </main>
  <footer class="site-footer">
    <p><a href="/">Startseite</a> · <a href="/datenschutz.html">Datenschutz</a> ·
      <a href="/impressum.html">Impressum</a></p>
  </footer>
  <script src="/bunny.js" defer></script>
</body>
</html>
"""


def inline_markdown(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r'(?<![">])(https://[^\s<),]+[^\s<),.])', r'<a href="\1">\1</a>', text)
    return text


def markdown_to_html(source: str) -> str:
    """Kleiner Markdown-Umwandler – reicht für PRIVACY.md (Überschriften, Absätze, Listen)."""
    out, paragraph, items = [], [], []

    def flush():
        if paragraph:
            out.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline_markdown(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in source.splitlines():
        stripped = line.strip()
        heading = re.match(r"(#{1,3}) (.+)", stripped)
        if not stripped:
            flush()
        elif heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
        elif stripped == "---":
            flush()
            out.append("<hr>")
        elif stripped.startswith("- "):
            if paragraph:
                flush()
            items.append(stripped[2:])
        elif items and line.startswith("  "):
            items[-1] += " " + stripped          # Fortsetzung eines Listenpunkts
        else:
            paragraph.append(stripped)
    flush()
    return "\n".join(out)


REQUIRED = ["name", "adresse", "email"]


def impressum_page() -> str:
    if not IMPRESSUM.exists():
        raise BuildError("website/impressum.json fehlt – Vorlage: website/impressum.example.json")
    data = json.loads(IMPRESSUM.read_text("utf-8"))
    missing = [key for key in REQUIRED if not str(data.get(key, "")).strip()]
    if missing:
        raise BuildError(f"Im Impressum fehlt noch: {', '.join(missing)}")

    e = {key: html.escape(str(value).strip()) for key, value in data.items()}
    address = "<br>".join(html.escape(part.strip()) for part in data["adresse"].split(","))
    extra = f"<p>UID-Nummer: {e['uid']}</p>" if e.get("uid") else ""
    body = f"""    <h1>Impressum</h1>
    <p>Informationen gemäß § 5 E-Commerce-Gesetz und Offenlegung gemäß § 25 Mediengesetz</p>
    <h2>Betreiber</h2>
    <p>{e['name']}<br>{address}</p>
    <p>E-Mail: <a href="mailto:{e['email']}">{e['email']}</a></p>
    {extra}
    <h2>Unternehmensgegenstand</h2>
    <p>Betrieb der Website malipin.com: Stil-Empfehlungen für Mode und Wohnen auf Basis von
      Pinterest-Boards und Vermittlung zu Online-Shops (teilweise über Affiliate-Links).</p>
    <h2>Grundlegende Richtung</h2>
    <p>Informationen und Produktempfehlungen rund um Mode, Wohnen und persönlichen Stil.</p>
    <h2>Hinweise</h2>
    <p>Malipin steht in keiner Verbindung zu Pinterest, eBay oder Etsy und wird von diesen
      nicht unterstützt oder geprüft. Für Inhalte externer Links sind deren Betreiber
      verantwortlich.</p>"""
    return subpage("Impressum", body, "Impressum und Offenlegung von Malipin (malipin.com).",
                   "/impressum.html")


def robots_txt() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"


def sitemap_xml(today: datetime.date | None = None) -> str:
    today = (today or datetime.date.today()).isoformat()
    urls = "".join(f"  <url><loc>{SITE_URL}{path}</loc><lastmod>{today}</lastmod></url>\n"
                   for path in PAGES)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n")


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    for name in COPY:
        shutil.copy(FRONTEND / name, OUT / name)
    (OUT / "index.html").write_text(static_index((FRONTEND / "index.html").read_text("utf-8")), "utf-8")
    privacy = markdown_to_html((ROOT / "PRIVACY.md").read_text("utf-8"))
    (OUT / "datenschutz.html").write_text(subpage(
        "Datenschutz", privacy, "Wie Malipin mit deinen Daten umgeht: nur Lesezugriff auf "
        "Pinterest, keine Weitergabe, Löschen jederzeit möglich.", "/datenschutz.html",
        lang="en"), "utf-8")   # PRIVACY.md ist (noch) Englisch
    (OUT / "impressum.html").write_text(impressum_page(), "utf-8")
    (OUT / "404.html").write_text(subpage("Nicht gefunden", "    <h1>Hoppla!</h1>\n"
        "    <p>Diese Seite gibt es nicht. Mali hat überall geschnuppert – nichts.</p>\n"
        '    <p><a class="button" href="/">Zur Startseite</a></p>'), "utf-8")
    (OUT / "robots.txt").write_text(robots_txt(), "utf-8")
    (OUT / "sitemap.xml").write_text(sitemap_xml(), "utf-8")
    print(f"Fertig: {OUT}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        sys.exit(1)
