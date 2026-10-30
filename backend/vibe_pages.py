"""Eine eigene Seite pro Vibe: /stil/goth-baddie, /stil/clean-girl …

Damit Google jeden Vibe einzeln findet (z.B. bei der Suche "goth baddie outfit") und geteilte
Links eine passende Vorschau haben. Der Inhalt kommt aus dem Stil-Lexikon (style_guide.py) und
wird hier auf dem Server als fertiges HTML gebaut. Kopf und Fuß stammen aus frontend/stile.html,
damit alle Seiten gleich aussehen.
"""

import re
from html import escape

from backend import i18n, secondhand, style_guide
from backend.config import FRONTEND_DIR

SITE_URL = "https://malipin.com"


def path(vibe_slug: str) -> str:
    """"vibe-goth-baddie" -> "/stil/goth-baddie"."""
    return "/stil/" + vibe_slug.removeprefix("vibe-")


def all_paths() -> list[str]:
    return [path(v["slug"]) for v in style_guide.guide("de")["vibes"]]


def _shell() -> tuple[str, str]:
    """Kopf (bis <main>) und Fuß (ab </main>) der Stile-Seite."""
    page = (FRONTEND_DIR / "stile.html").read_text("utf-8")
    head, rest = page.split('<main class="styles-page">', 1)
    foot = rest.split("</main>", 1)[1]
    foot = foot.replace('  <script src="/stile.js"></script>\n', "")
    head = head.replace("<body data-big-mali>", "<body>")
    return head, foot


def _meta(head: str, *, title: str, description: str, url: str) -> str:
    title, description = escape(title), escape(description)
    head = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", head)
    head = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*',
                  lambda m: m.group(1) + description, head)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + title, head)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + url, head)
    head = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + url, head)
    return head


def render(name: str) -> str | None:
    """HTML der Vibe-Seite, None wenn es den Vibe nicht gibt."""
    lang = i18n.current()
    guide = style_guide.guide(lang)
    vibe = next((v for v in guide["vibes"] if v["slug"] == f"vibe-{name}"), None)
    if vibe is None:
        return None
    tr = lambda text, **values: escape(i18n.tr(text, lang, **values))  # noqa: E731
    title = escape(vibe["title"])

    pieces = "".join(f"<li>{escape(p)}</li>" for p in vibe["pieces"])
    swatches = "".join(f'<span class="swatch" style="background:{escape(c)}"></span>'
                       for c in vibe["colors"])
    styles = "".join(f'<a class="chip" href="/stile.html#{escape(s["slug"])}">{escape(s["name"])}</a>'
                     for s in vibe["styles"])
    quote = (f'<blockquote class="vibe-mali"><span class="vibe-mali-label">{tr("Mali sagt")}</span>'
             f"<span>{escape(_no_emoji(vibe['mali']))}</span></blockquote>" if vibe["mali"] else "")
    # Typische Teile second hand suchen (Vinted/willhaben, nur Such-Links, backend/secondhand.py)
    used = "".join(
        f'<p class="secondhand-links"><span>{escape(site)}:</span> ' + " ".join(
            f'<a class="chip" href="{escape(secondhand.search_url(site, [piece]))}" target="_blank" '
            f'rel="noopener">{escape(piece)}</a>' for piece in vibe["pieces"]) + "</p>"
        for site in secondhand.sites())
    used = (f'<h3 class="vibe-sub">{tr("Second Hand im {title}-Vibe", title=vibe["title"])}</h3>'
            + used if used else "")
    others = "".join(f'<a class="chip" href="{path(v["slug"])}">{escape(v["title"])}</a>'
                     for v in guide["vibes"] if v["slug"] != vibe["slug"])
    from backend import outfit_pages   # hier, sonst importieren sich beide Dateien gegenseitig
    outfits = "".join(f'<a class="chip" href="{outfit_pages.path(p.slug)}">{escape(p.title)}</a>'
                      for p in outfit_pages.PAGES if name in p.related)
    outfits = (f'<h2 class="styles-heading">{tr("Komplette Outfits")}</h2>'
               f'<div class="vibe-others">{outfits}</div>' if outfits else "")

    main = f"""<main class="styles-page vibe-page">
    <nav class="vibe-crumbs" aria-label="{tr("Pfad")}"><a href="/stile.html">{tr("Stil-Lexikon")}</a> <span aria-hidden="true">›</span> {title}</nav>
    <article class="vibe-card look-{escape(vibe["look"])}" data-vibe="{escape(vibe["slug"])}">
      <header class="vibe-card-head"><h1 class="vibe-title">{title}</h1></header>
      {quote}
      <p class="vibe-about">{escape(vibe["about"])}</p>
      <h2 class="vibe-sub">{tr("Typische Teile")}</h2>
      <ul class="vibe-pieces">{pieces}</ul>
      <div class="vibe-foot"><div class="vibe-swatches" aria-hidden="true">{swatches}</div><div class="vibe-styles">{styles}</div></div>
    </article>

    <section class="needs-input vibe-cta">
      <h2>{tr("Finde Teile im {title}-Vibe", title=vibe["title"])}</h2>
      <p class="muted">{tr("Lade ein Outfit-Foto hoch, das dir gefällt. Mali sucht dir ähnliche Teile, neu und Second Hand.")}</p>
      <a class="button" href="/foto.html">{tr("Foto hochladen")}</a>
      {used}
    </section>

    {outfits}
    <h2 class="styles-heading">{tr("Weitere Vibes")}</h2>
    <div class="vibe-others">{others}</div>
  </main>"""

    head, foot = _shell()
    page_title = i18n.tr("{title} Vibe, Bedeutung und typische Teile | Malipin", lang,
                         title=vibe["title"])
    head = _meta(head, title=page_title, description=vibe["about"],
                 url=SITE_URL + path(vibe["slug"]))
    head = head.replace('<html lang="de">', f'<html lang="{lang}">')
    return head + main + foot


def _no_emoji(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\U0001F000-\U0001FAFF☀-➿️‍]", "", text)).strip()
