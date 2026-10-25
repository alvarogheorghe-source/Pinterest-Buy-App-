"""Erzeugt das Malipin-Logo: Mali als Pinnadel 🐰📍 + Schriftzug "malipin".

Mali ist der Kopf der Pinnadel, unten läuft sie in eine rosa Spitze aus ("Mali" + "Pin").
Gezeichnet wird – wie Mali in bunny.js – mit einem Raster aus Buchstaben. Zum Umzeichnen
Buchstaben in PIN ändern und das Skript neu starten.

Starten:   python scripts/make_logo.py
Ergebnis:  frontend/img/favicon.svg (Browser-Tab-Symbol) und das Logo in jeder Seite
           (zwischen <!-- logo --> und <!-- /logo -->)
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

# Gleiche Farben wie Mali (bunny.js) + Rosa der Website für die Nadelspitze
PALETTE = {
    "o": "#6b5656",  # Umriss
    "w": "#fffaf6",  # Fell
    "s": "#f1e1da",  # Fell-Schatten
    "p": "#f6a5b9",  # rosa: Ohren innen, Nase
    "b": "#ffc7d1",  # Bäckchen
    "k": "#2d2326",  # Augen
    "P": "#c93a69",  # Nadelspitze (Akzentfarbe der Website)
    "L": "#e8789a",  # Glanzlicht auf der Spitze
    "h": "#f3c6d3",  # kleiner Schatten am Boden
}

# 16 × 18 Pixel. Zeilen 0–4 = Ohren (wackeln), "k" = Augen (blinzeln)
PIN = [
    "....oo....oo....",
    "...owwo..owwo...",
    "...owpo..opwo...",
    "...owpo..opwo...",
    "...owwoooowwo...",
    "..owwwwwwwwwwo..",
    ".owwwwwwwwwwwwo.",
    ".owwkkwwwwkkwwo.",
    ".owbkkwwwwkkbwo.",
    ".owwwwwppwwwwwo.",
    ".oswwwwwwwwwwso.",
    "..osswwwwwwsso..",
    "...ooPPPPPPoo...",
    ".....oLPPPPo....",
    "......oLPPo.....",
    ".......oPo......",
    "........o.......",
    "......hhhh......",
]
EAR_ROWS = range(0, 5)


def rects(rows: list[str], offset: int = 0, only: str | None = None, skip: str = "") -> str:
    """Pixel -> SVG-Rechtecke. Gleiche Farben nebeneinander werden zu einem Rechteck."""
    out = []
    for y, row in enumerate(rows, start=offset):
        x = 0
        while x < len(row):
            char = row[x]
            run = 1
            while x + run < len(row) and row[x + run] == char:
                run += 1
            if char != "." and (only is None or char in only) and char not in skip:
                out.append(f'<rect x="{x}" y="{y}" width="{run}" height="1" fill="{PALETTE[char]}"/>')
            x += run
    return "".join(out)


def pin_svg(css_class: str = "", standalone: bool = False) -> str:
    """Das Pinnadel-Symbol. Ohren und Augen sind eigene Gruppen, damit CSS sie bewegen kann."""
    ears = rects(PIN[:5], 0)
    eyes = rects(PIN[5:], 5, only="k")
    rest = rects(PIN[5:], 5, skip="k")
    attrs = ' xmlns="http://www.w3.org/2000/svg"' if standalone else ""
    cls = f' class="{css_class}"' if css_class else ""
    return (f'<svg{attrs}{cls} viewBox="0 0 16 18" shape-rendering="crispEdges" aria-hidden="true">'
            f'<g class="logo-ears">{ears}</g><g>{rest}</g><g class="logo-eyes">{eyes}</g></svg>')


# Pixel-Herz als i-Punkt (5 × 4)
HEART = ["oo.oo", "ooooo", ".ooo.", "..o.."]


def heart_svg() -> str:
    # Farbe kommt aus CSS (fill: var(--accent)), darum hier ein Platzhalter
    cells = re.sub(r' fill="[^"]*"', "", rects(HEART))
    return (f'<svg class="logo-heart" viewBox="0 0 5 4" shape-rendering="crispEdges" '
            f'aria-hidden="true">{cells}</svg>')


def i_with_heart() -> str:
    # Punktloses ı + Herz darüber
    return f'<span class="logo-i">ı{heart_svg()}</span>'


def logo_html() -> str:
    return (
        '<a href="/" class="logo" aria-label="Malipin – Startseite">'
        + pin_svg("logo-pin")
        + '<span class="logo-word"><span class="logo-mali">mal' + i_with_heart() + '</span>'
        + '<span class="logo-pinword">p' + i_with_heart() + 'n</span></span></a>'
    )


def main() -> None:
    (FRONTEND / "img").mkdir(exist_ok=True)
    (FRONTEND / "img" / "favicon.svg").write_text(pin_svg(standalone=True) + "\n", encoding="utf-8")

    block = re.compile(r"<!-- logo -->.*?<!-- /logo -->", re.DOTALL)
    for page in sorted(FRONTEND.glob("*.html")):
        html = page.read_text(encoding="utf-8")
        new = block.sub(f"<!-- logo -->{logo_html()}<!-- /logo -->", html)
        if new != html:
            page.write_text(new, encoding="utf-8")
            print(f"Logo aktualisiert: {page.name}")
    print("Fertig: frontend/img/favicon.svg")


if __name__ == "__main__":
    main()
