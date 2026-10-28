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

from scripts import i18n, seo

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT = ROOT / "site"
IMPRESSUM = ROOT / "website" / "impressum.json"

COPY = ["style.css", "landing.css", "bunny.css", "bunny.js", "site.webmanifest",
        "img/favicon.svg", "img/favicon-48.png", "img/apple-touch-icon.png",
        "img/icon-192.png", "img/icon-512.png", "img/og-image.png", "img/og-image-en.png"]
SOON = "Bald verfügbar"
SITE_URL = "https://malipin.com"
# Seiten für Google (sitemap.xml) – 404 bewusst nicht
PAGES = ["/", "/en/", "/datenschutz.html", "/impressum.html"]
# Startseite in zwei Sprachen: Sprache -> Adresse
LANGUAGES = {"de": "/", "en": "/en/"}


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
    page = re.sub(r'\s*<a href="/stile\.html"[^>]*>.*?</a>', "", page, flags=re.DOTALL)
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
    page = page.replace('  <script src="/nav.js" defer></script>\n', "")
    page = page.replace('  <!-- Sprache (Deutsch/Englisch) – vor allen anderen Skripten -->\n'
                        '  <script src="/i18n-en.js"></script>\n  <script src="/i18n.js"></script>\n', "")
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
    alternates = "".join(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{SITE_URL}{path}"/>\n'
                         for lang, path in LANGUAGES.items())
    urls = "".join(f"  <url>\n    <loc>{SITE_URL}{path}</loc>\n    <lastmod>{today}</lastmod>\n"
                   + (alternates if path in LANGUAGES.values() else "") + "  </url>\n"
                   for path in PAGES)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            f"{urls}</urlset>\n")


# --- Zweisprachige Startseite (/ = Deutsch, /en/ = Englisch) -----------------------------------

LANG_HINT = """
  <!-- Englischsprachiger Browser? Kleiner Hinweis auf die englische Seite (kein Zwangs-Umleiten) -->
  <div class="lang-hint" id="lang-hint" hidden>
    <span>This page is also available in English.</span>
    <a href="/en/" hreflang="en" lang="en">Switch to English</a>
    <button type="button" aria-label="Close" id="lang-hint-close">×</button>
  </div>
  <script>
    (() => {
      const hint = document.getElementById("lang-hint");
      let dismissed = false;
      try { dismissed = localStorage.getItem("malipin-lang-hint") === "no"; } catch {}
      const german = (navigator.languages || [navigator.language || ""]).some((l) => l.startsWith("de"));
      if (!german && !dismissed) hint.hidden = false;
      document.getElementById("lang-hint-close").addEventListener("click", () => {
        hint.hidden = true;
        try { localStorage.setItem("malipin-lang-hint", "no"); } catch {}
      });
    })();
  </script>
"""


def _alternates() -> str:
    links = "".join(f'  <link rel="alternate" hreflang="{lang}" href="{SITE_URL}{path}">\n'
                    for lang, path in LANGUAGES.items())
    return links + f'  <link rel="alternate" hreflang="x-default" href="{SITE_URL}/en/">\n'


def _switch(to_lang: str) -> str:
    label = {"de": "Deutsch", "en": "English"}[to_lang]
    return (f'<a href="{LANGUAGES[to_lang]}" class="header-link lang-switch" hreflang="{to_lang}" '
            f'lang="{to_lang}" aria-label="{label}">{to_lang.upper()}</a>')


def localize(page: str, lang: str) -> str:
    """Sprachumschalter, hreflang-Links; für Englisch zusätzlich Adresse, Vorschau, JSON-LD."""
    other = "en" if lang == "de" else "de"
    page = page.replace('  <link rel="canonical"', _alternates() + '  <link rel="canonical"', 1)
    page = page.replace('<nav class="header-nav">', f'<nav class="header-nav">\n      {_switch(other)}', 1)
    page = page.replace('<nav class="footer-links">',
                        f'<nav class="footer-links">\n        {_switch(other)}', 1)
    if lang == "de":   # Hinweis ganz oben, direkt nach <body …>
        return re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + LANG_HINT, page, count=1)
    url = f"{SITE_URL}/en/"
    page = page.replace('<html lang="de">', '<html lang="en">', 1)
    page = page.replace(f'<link rel="canonical" href="{SITE_URL}/">', f'<link rel="canonical" href="{url}">')
    page = page.replace(f'<meta property="og:url" content="{SITE_URL}/">', f'<meta property="og:url" content="{url}">')
    page = page.replace('<meta property="og:locale" content="de_AT">',
                        '<meta property="og:locale" content="en_US">\n'
                        '  <meta property="og:locale:alternate" content="de_AT">')
    page = page.replace("/img/og-image.png", "/img/og-image-en.png")
    page = page.replace('<a href="/" class="logo"', '<a href="/en/" class="logo"')
    return seo.render(page, url, "en")


def english_index(german: str) -> str:
    translations, same = i18n.load()
    missing = i18n.missing(german, translations, same)
    if missing:
        raise BuildError("Englische Übersetzung fehlt in frontend/i18n/en.json für:\n  - "
                         + "\n  - ".join(missing))
    return localize(i18n.translate(german, translations), "en")


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    for name in COPY:
        shutil.copy(FRONTEND / name, OUT / name)
    german = static_index((FRONTEND / "index.html").read_text("utf-8"))
    (OUT / "en").mkdir()
    (OUT / "en" / "index.html").write_text(english_index(german), "utf-8")
    (OUT / "index.html").write_text(localize(german, "de"), "utf-8")
    privacy = markdown_to_html((ROOT / "PRIVACY.md").read_text("utf-8"))
    (OUT / "datenschutz.html").write_text(subpage(   # PRIVACY.md ist (noch) Englisch
        "Privacy Policy", privacy, "How Malipin handles your data: read-only Pinterest access, "
        "no sharing, delete any time.", "/datenschutz.html", lang="en"), "utf-8")
    # Gleiche Seite unter englischer Adresse (z.B. für die Pinterest-Bewerbung)
    (OUT / "privacy.html").write_text(subpage(
        "Privacy Policy", privacy, "How Malipin handles your data: read-only Pinterest access, "
        "no sharing, delete any time.", "/privacy.html", lang="en"), "utf-8")
    (OUT / "impressum.html").write_text(impressum_page(), "utf-8")
    (OUT / "404.html").write_text(subpage("Nicht gefunden / Not found", "    <h1>Hoppla! / Oops!</h1>\n"
        "    <p>Diese Seite gibt es nicht. Mali hat überall geschnuppert – nichts.</p>\n"
        '    <p lang="en">This page doesn\'t exist. Mali sniffed everywhere – nothing.</p>\n'
        '    <p><a class="button" href="/">Zur Startseite</a> '
        '<a class="button secondary" href="/en/" lang="en">Go to homepage</a></p>'), "utf-8")
    (OUT / "robots.txt").write_text(robots_txt(), "utf-8")
    (OUT / "sitemap.xml").write_text(sitemap_xml(), "utf-8")
    print(f"Fertig: {OUT}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        sys.exit(1)
