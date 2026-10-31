"""Outfit-Seiten für Google und Pinterest: /outfits/clean-girl-outfit-unter-50 usw.

Jede Seite beantwortet eine Suche, die viele junge Leute eingeben ("y2k outfit herren",
"clean girl outfit unter 50 euro"): ein kurzer Text, wie der Look funktioniert, und ein
fertiges Outfit aus ECHTEN Produkten im Budget, dazu weitere passende Teile.

Die Produkte sind nie fest eingetragen: Bei jedem Aufruf (höchstens stündlich neu gerechnet)
kommen sie aus dem aktuellen Katalog (nächtlicher Feed-Import, feeds.py). Neue Shops,
neue Preise, ausverkaufte Teile – die Seiten passen sich von selbst an.

Neue Seite: einen Eintrag in PAGES ergänzen (Test: tests/test_outfit_pages.py).
Lieber wenige gute Seiten mit eigenem Text als viele leere – Google bestraft Massenware.
"""

import itertools
import re
import time
from dataclasses import dataclass, field
from html import escape
from urllib.parse import quote

from backend import (currency, feeds, product_checks, products, quality, region, secondhand,
                     style_guide)
from backend.matching import build_style_profile, rank_products
from backend.vibe_pages import SITE_URL, _meta, _shell

CACHE_SECONDS = 3600
MORE = 12              # so viele weitere Teile unter dem Outfit
CANDIDATES = 8         # so viele beste Teile je Platz werden für das Outfit kombiniert
GENDER_BONUS = 1.0     # ausdrücklich Damen/Herren schlägt "unbekannt"
# Teile, die auf einer Herren-Seite ohne Angabe sicher falsch wären (und umgekehrt)
NOT_FOR = {"herren": re.compile(r"ballerina|pumps|heels|mary jane|bluse|minirock|kleid|bikini|crop|bh\b", re.I),
           "damen": re.compile(r"krawatte|boxershorts", re.I)}


@dataclass
class OutfitPage:
    slug: str
    title: str                 # H1 = die Suche, für die die Seite gefunden werden soll
    description: str           # für Google (ca. 150 Zeichen)
    intro: str
    tips: list[str]
    keywords: str              # wonach im Katalog gesucht wird (Stil, Teile, Farben)
    slots: list[str]           # ein Teil je Kategorie, in dieser Reihenfolge
    budget: float              # Gesamtpreis des Outfits höchstens (in der Währung der Person)
    gender: str | None = None
    related: list[str] = field(default_factory=list)   # passende /stil/-Seiten


PAGES = [
    OutfitPage(
        "clean-girl-outfit-unter-50", "Clean Girl Outfit unter 50 €",
        "Clean Girl Look nachstylen: ruhige Farben, klare Schnitte, goldene Details. "
        "Ein komplettes Outfit aus echten Shops für unter 50 €.",
        "Der Clean Girl Look wirkt mühelos, ist aber gut durchdacht: ruhige Farben wie Weiß, "
        "Beige und Creme, klare Schnitte und ein, zwei goldene Details. Teuer muss er nicht sein. "
        "Wichtiger als Marken sind saubere Linien und Teile, die gut zusammenpassen.",
        ["Bleib bei zwei bis drei Farben, am besten Weiß, Beige und ein warmer Ton.",
         "Ein schlichtes Oberteil und eine gut sitzende Hose sind die Basis.",
         "Goldene Creolen oder eine feine Kette machen den Look fertig."],
        "clean minimalistisch beige weiß creme gold basic", ["Oberteile", "Hosen", "Schuhe",
                                                             "Accessoires"], 50, "damen",
        ["clean-girl", "quiet-luxury"]),
    OutfitPage(
        "y2k-outfit-herren", "Y2K Outfit Herren",
        "Y2K Outfits für Herren: Baggy Jeans, Grafik-Shirts und auffällige Sneaker. "
        "Ein komplettes Outfit aus echten Shops für unter 80 €.",
        "Der Y2K-Look holt die frühen 2000er zurück: weite Jeans, Grafik-Shirts, sportliche "
        "Sneaker und gern ein bisschen Glanz. Bei Herren funktioniert er am besten locker und "
        "weit geschnitten, mit einem Teil, das heraussticht.",
        ["Weite oder Baggy Jeans sind das Herzstück.",
         "Ein Grafik- oder Logo-Shirt bringt den Retro-Vibe.",
         "Dazu sportliche Sneaker, gern mit dicker Sohle."],
        "y2k baggy jeans grafik shirt retro sneaker", ["Oberteile", "Hosen", "Schuhe"], 80,
        "herren", ["y2k-baby", "streetwear-icon"]),
    OutfitPage(
        "y2k-outfit-damen", "Y2K Outfit Damen",
        "Y2K Outfits für Damen: Baby Tees, Low Rise Jeans und verspielte Details. "
        "Ein komplettes Outfit aus echten Shops für unter 60 €.",
        "Y2K bei Damen heißt: kurze Baby Tees, tief sitzende oder weite Jeans, Glitzer und "
        "verspielte Accessoires. Der Look lebt von Mut zur Farbe und von Teilen, die ein "
        "bisschen nach Musikvideo aus dem Jahr 2003 aussehen.",
        ["Ein kurzes Baby Tee oder Top ist fast Pflicht.",
         "Low Rise oder weite Jeans, gern in hellen Waschungen.",
         "Kleine Taschen, Haarspangen und Glitzer machen den Look."],
        "y2k baby tee low rise jeans glitzer pink", ["Oberteile", "Hosen", "Schuhe"], 60,
        "damen", ["y2k-baby", "coquette-era"]),
    OutfitPage(
        "streetwear-outfit-herren-unter-100", "Streetwear Outfit Herren unter 100 €",
        "Streetwear für Herren mit kleinem Budget: Hoodie, Cargohose, Sneaker. "
        "Ein komplettes Outfit aus echten Shops für unter 100 €.",
        "Streetwear lebt von bequemen, weiten Schnitten und einem Teil, das auffällt. Die Basis "
        "sind ein Oversized-Hoodie oder ein schweres Shirt, eine Cargo- oder weite Hose und gute "
        "Sneaker. Teure Marken braucht es dafür nicht.",
        ["Oversized oben, weit unten: das ist die Silhouette.",
         "Erdtöne, Schwarz und Grau lassen sich endlos kombinieren.",
         "Die Sneaker sind das Statement-Teil."],
        "streetwear oversized hoodie cargo sneaker", ["Oberteile", "Hosen", "Schuhe"], 100,
        "herren", ["streetwear-icon", "effortless-cool"]),
    OutfitPage(
        "streetwear-outfit-damen", "Streetwear Outfit Damen",
        "Streetwear für Damen: Oversized-Hoodie, Cargohose, Chunky Sneaker. "
        "Ein komplettes Outfit aus echten Shops für unter 100 €.",
        "Streetwear bei Damen spielt mit Gegensätzen: weite Hosen mit kurzem Top, ein großer "
        "Hoodie mit Radlerhose, dazu Chunky Sneaker. Bequem, selbstbewusst und mit einem Teil, "
        "über das man redet.",
        ["Spiel mit weit und kurz: Cargohose zu einem kurzen Top.",
         "Chunky Sneaker geben dem Look Gewicht.",
         "Eine Cap oder eine kleine Tasche als Detail."],
        "streetwear oversized cargo hoodie chunky sneaker", ["Oberteile", "Hosen", "Schuhe"], 100,
        "damen", ["streetwear-icon", "athleisure-era"]),
    OutfitPage(
        "cozy-herbst-outfit", "Cozy Herbst Outfit",
        "Gemütliche Herbst-Outfits: Strick, warme Erdtöne, bequeme Schnitte. "
        "Ein komplettes Outfit aus echten Shops für unter 80 €.",
        "Ein cozy Herbst-Outfit fühlt sich an wie eine Decke, sieht aber trotzdem gut aus: "
        "weicher Strick, warme Farben wie Beige, Braun und Creme und Schnitte, in denen man den "
        "ganzen Tag bleiben will.",
        ["Ein Oversized-Strickpulli ist der Mittelpunkt.",
         "Warme Erdtöne: Beige, Camel, Braun, Creme.",
         "Bequeme Stiefel oder Sneaker für lange Spaziergänge."],
        "cozy strick oversized beige braun warm herbst", ["Oberteile", "Hosen", "Schuhe"], 80,
        "damen", ["cozy-era", "cottagecore"]),
    OutfitPage(
        "old-money-outfit-herren", "Old Money Outfit Herren",
        "Old Money Look für Herren: Strick, Hemd, Chino, Loafer. Zeitlos und elegant. "
        "Ein komplettes Outfit aus echten Shops für unter 120 €.",
        "Old Money sieht nach altem Geld aus, ohne laut zu sein: gedeckte Farben, Strick über dem "
        "Hemd, Chinos und Loafer. Keine Logos, dafür gute Passform und Teile, die auch in zehn "
        "Jahren noch funktionieren.",
        ["Keine großen Logos, lieber gute Stoffe und Passform.",
         "Navy, Beige, Weiß und Dunkelgrün sind die Grundfarben.",
         "Loafer statt Sneaker machen den Unterschied."],
        "klassisch elegant hemd strick chino loafer navy", ["Oberteile", "Hosen", "Schuhe"], 120,
        "herren", ["quiet-luxury", "clean-fit"]),
    OutfitPage(
        "old-money-outfit-damen", "Old Money Outfit Damen",
        "Old Money Look für Damen: Blazer, Strick, Stoffhose, Ballerinas. Zeitlos und elegant. "
        "Ein komplettes Outfit aus echten Shops für unter 120 €.",
        "Der Old Money Look bei Damen ist ruhig und hochwertig: ein Blazer oder Strick, eine "
        "Stoffhose mit Bügelfalte, Ballerinas oder Loafer. Wenige Teile, gedeckte Farben und "
        "nichts, was nach Trend schreit.",
        ["Gedeckte Farben: Creme, Navy, Camel.",
         "Eine Stoffhose mit Bügelfalte wirkt sofort elegant.",
         "Perlen oder schlichter Goldschmuck als Detail."],
        "klassisch elegant blazer strick stoffhose ballerinas", ["Oberteile", "Hosen", "Schuhe"],
        120, "damen", ["quiet-luxury", "clean-girl"]),
    OutfitPage(
        "gorpcore-outfit", "Gorpcore Outfit",
        "Gorpcore: Outdoor-Kleidung als Streetstyle. Fleece, Cargohose, Trail-Sneaker. "
        "Ein komplettes Outfit aus echten Shops für unter 150 €.",
        "Gorpcore trägt Outdoor-Kleidung in der Stadt: Fleecejacken, technische Hosen und "
        "Trail-Sneaker, gern in Erdtönen oder mit einem knalligen Farbakzent. Praktisch, "
        "wetterfest und gerade sehr gefragt.",
        ["Eine Fleece- oder Funktionsjacke ist das Hauptteil.",
         "Cargo- oder Wanderhosen mit vielen Taschen.",
         "Trail-Sneaker oder robuste Boots."],
        "outdoor utility fleece cargo wander trail", ["Jacken", "Hosen", "Schuhe"], 150, None,
        ["gorpcore", "athleisure-era"]),
    OutfitPage(
        "goth-outfit-damen", "Goth Outfit Damen",
        "Goth Outfits für Damen: Schwarz, Spitze, Boots und dunkle Details. "
        "Ein komplettes Outfit aus echten Shops für unter 80 €.",
        "Goth ist mehr als nur Schwarz: Spitze, Netz, Leder-Optik und schwere Boots, dazu "
        "silberne Details. Der Look ist dunkel, aber nicht langweilig, und lässt sich von "
        "dezent bis auffällig tragen.",
        ["Schwarz in verschiedenen Materialien wirkt spannender als nur Baumwolle.",
         "Schwere Boots oder Plateauschuhe sind die Basis.",
         "Silberschmuck und ein Choker als Detail."],
        "goth schwarz spitze grunge boots", ["Oberteile", "Kleider & Röcke", "Schuhe"], 80,
        "damen", ["goth-baddie"]),
]
BY_SLUG = {p.slug: p for p in PAGES}
_cache: dict = {}


def path(slug: str) -> str:
    return f"/outfits/{slug}"


def all_paths() -> list[str]:
    return ["/outfits", *(path(p.slug) for p in PAGES)]


def catalog() -> list[products.Product]:
    """Der nächtlich importierte Katalog (für alle gleich); ohne Feeds die Beispielprodukte."""
    return feeds.stored_products() or products.JsonProductSource().load()


def _price(item: dict) -> float | None:
    """Preis in der Währung der Person (None, wenn kein Umrechnungskurs da ist)."""
    return currency.convert(item["price"], item["currency"], region.current().currency,
                            currency.rates())


def money(amount: float) -> str:
    """"€ 24,99"; ganze Beträge ohne Komma ("€ 50" fürs Budget)."""
    code = region.current().currency
    symbol = {"EUR": "€", "GBP": "£", "USD": "$", "CHF": "CHF", "CAD": "CA$", "AUD": "A$"}
    text = f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{symbol.get(code, code)} {text}"


def candidates(page: OutfitPage) -> list[dict]:
    """Passende Teile im Budget, beste zuerst (gleiche Filter wie der Shop)."""
    here = region.current()
    selection = products.filter_products(catalog(), None, page.budget, None, "mode",
                                         currency=here.currency, country=here.code)
    selection = [p for p in selection
                 if not product_checks.is_ai(p.id) and not quality.luxury_in(p.name)
                 and p.category in page.slots + ["Jacken", "Accessoires"]]
    gender_of = {p.id: p.gender or product_checks.image_gender(p.id) for p in selection}
    if page.gender:
        selection = [p for p in selection if gender_of[p.id] in (page.gender, None)
                     and not (gender_of[p.id] is None and NOT_FOR[page.gender].search(p.name))]
    profile = build_style_profile([{"id": page.slug, "title": page.keywords, "description": ""}],
                                  "mode")
    ranked = [r for r in rank_products(selection, profile) if r["score"] > 0]
    for item in ranked:
        item["local_price"] = _price(item)
        if page.gender and gender_of[item["id"]] == page.gender:
            item["score"] = round(item["score"] + GENDER_BONUS, 3)
    ranked.sort(key=lambda r: (-r["score"], r["price"]))
    return [r for r in ranked if r["local_price"] is not None]


def outfit(page: OutfitPage, ranked: list[dict]) -> list[dict]:
    """Ein Teil je Platz, zusammen im Budget, mit möglichst hoher Passung. Passt nicht alles
    ins Budget, lieber ein Teil weniger (mindestens zwei) als gar kein Outfit."""
    per_slot = [[r for r in ranked if r["category"] == slot][:CANDIDATES] for slot in page.slots]
    per_slot = [options for options in per_slot if options]     # leere Plätze auslassen
    for size in range(len(per_slot), 1, -1):                    # erst alle Plätze, dann weniger
        best, best_score = [], -1.0
        for slots in itertools.combinations(per_slot, size):
            for combo in itertools.product(*slots):
                total = sum(item["local_price"] for item in combo)
                score = sum(item["score"] for item in combo)
                if total <= page.budget and score > best_score:
                    best, best_score = list(combo), score
        if best:
            return best
    return []


def _card(item: dict) -> str:
    return (f'<a class="outfit-item" href="/produkt.html?id={quote(item["id"])}">'
            f'<img src="{escape(item["image_url"])}" alt="{escape(item["name"])}" loading="lazy">'
            f'<span class="outfit-item-cat">{escape(item["category"])}</span>'
            f'<span class="outfit-item-name">{escape(item["name"])}</span>'
            f'<strong class="outfit-item-price">{money(item["local_price"])}</strong></a>')


def render(slug: str) -> str | None:
    page = BY_SLUG.get(slug)
    if page is None:
        return None
    key = (slug, region.current().code)
    cached = _cache.get(key)
    if cached and cached[0] > time.time() - CACHE_SECONDS:
        return cached[1]
    html = _render(page)
    _cache[key] = (time.time(), html)
    return html


def _render(page: OutfitPage) -> str:
    ranked = candidates(page)
    look = outfit(page, ranked)
    chosen = {item["id"] for item in look}
    more = [r for r in ranked if r["id"] not in chosen][:MORE]
    total = sum(item["local_price"] for item in look)

    if look:
        outfit_html = (f'<div class="outfit-grid">{"".join(_card(i) for i in look)}</div>'
                       f'<p class="outfit-total">Zusammen: <strong>{money(total)}</strong> '
                       f'<span class="muted">· Preise von heute, Mali sucht täglich neu</span></p>')
    else:
        outfit_html = ('<p class="muted">Gerade findet Mali kein komplettes Outfit im Budget. '
                       'Schau morgen wieder vorbei, der Katalog wird jede Nacht neu geladen.</p>')
    more_html = (f'<h2 class="styles-heading">Mehr Teile für den Look</h2>'
                 f'<div class="outfit-grid more">{"".join(_card(i) for i in more)}</div>'
                 if more else "")
    used = "".join(
        f'<p class="secondhand-links"><span>{escape(site)}:</span> ' + " ".join(
            f'<a class="chip" href="{escape(secondhand.search_url(site, [slot, page.gender or ""]))}" '
            f'target="_blank" rel="noopener">{escape(slot)}</a>' for slot in page.slots) + "</p>"
        for site in secondhand.sites())
    tips = "".join(f"<li>{escape(tip)}</li>" for tip in page.tips)
    titles = {v["slug"].removeprefix("vibe-"): v["title"] for v in style_guide.guide("de")["vibes"]}
    related = "".join(f'<a class="chip" href="/stil/{escape(v)}">{escape(titles.get(v, v))}</a>'
                      for v in page.related)
    others = "".join(f'<a class="chip" href="{path(p.slug)}">{escape(p.title)}</a>'
                     for p in PAGES if p.slug != page.slug)

    main = f"""<main class="styles-page outfit-page">
    <nav class="vibe-crumbs" aria-label="Pfad"><a href="/outfits">Outfit-Ideen</a> <span aria-hidden="true">›</span> {escape(page.title)}</nav>
    <h1 class="outfit-title">{escape(page.title)}</h1>
    <p class="outfit-intro">{escape(page.intro)}</p>

    <h2 class="styles-heading">Malis Outfit unter {money(page.budget)}</h2>
    {outfit_html}

    <h2 class="styles-heading">So stylst du den Look</h2>
    <ul class="outfit-tips">{tips}</ul>

    {more_html}

    <section class="vibe-cta">
      <h2>Du hast ein Outfit gesehen, das dir gefällt?</h2>
      <p class="muted">Lade ein Foto hoch. Mali findet ähnliche Teile, neu und Second Hand.</p>
      <a class="button" href="/foto.html">Foto hochladen</a>
      {'<h3 class="vibe-sub">Second Hand finden</h3>' + used if used else ""}
    </section>

    {'<h2 class="styles-heading">Passende Vibes</h2><div class="vibe-others">' + related + "</div>" if related else ""}
    <h2 class="styles-heading">Weitere Outfit-Ideen</h2>
    <div class="vibe-others">{others}</div>
  </main>"""
    head, foot = _shell()
    head = _meta(head, title=f"{page.title} | Malipin", description=page.description,
                 url=SITE_URL + path(page.slug))
    return head + main + foot


def render_index() -> str:
    items = "".join(
        f'<a class="outfit-link" href="{path(p.slug)}"><strong>{escape(p.title)}</strong>'
        f'<span class="muted">{escape(p.description.split(". ")[0])}.</span></a>' for p in PAGES)
    main = f"""<main class="styles-page outfit-page">
    <h1 class="outfit-title">Outfit-Ideen</h1>
    <p class="outfit-intro">Komplette Looks aus echten Shops, jeden Tag neu zusammengestellt und
    immer im Budget. Such dir einen Stil aus, Mali hat das Outfit schon fertig.</p>
    <div class="outfit-links">{items}</div>
  </main>"""
    head, foot = _shell()
    head = _meta(head, title="Outfit-Ideen mit Budget | Malipin",
                 description="Komplette Outfits aus echten Shops, im Budget: Clean Girl, Y2K, "
                             "Streetwear, Old Money, Gorpcore und mehr. Täglich neu.",
                 url=SITE_URL + "/outfits")
    return head + main + foot
