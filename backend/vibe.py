"""Malis Vibe-Check: Welchen Vibe gibt dein Pinterest ab? Immer positiv!

Jeder Vibe hat Begriffe (Stile, Farben) mit Gewichten. Wir rechnen für jeden Vibe:
    Punkte = Summe( Gewicht × Anteil der Pins mit diesem Begriff )
Der Vibe mit den meisten Punkten gewinnt. Ist ein zweiter fast so stark, kommt er
als "mit einer Prise …" dazu. Die Sprüche werden zufällig gewählt, damit Mali
bei jedem Klick etwas Neues sagt.

Neue Vibes oder Sprüche? Einfach unten in VIBES ergänzen.
"""

import random
from dataclasses import dataclass

from backend.matching import StyleProfile, build_style_profile

# Farbtupfer für die Vibe-Karte zum Teilen (frontend/vibecard.js)
SWATCHES = {
    "beige": "#d8c3a5", "weiß": "#f6f1e9", "schwarz": "#1e1e1e", "grau": "#9b9a9e",
    "braun": "#7b5a3c", "blau": "#5a82b4", "grün": "#7a9e7e", "oliv": "#6b7048",
    "rosa": "#e8b4bc", "rot": "#b42832", "orange": "#c8693f", "gelb": "#e1be3c",
    "silber": "#c4c6cc", "gold": "#c9a54a",
}

# Look der Vibe-Karte (Hintergrund + Malis Outfit, siehe frontend/vibecard.js).
# Wenige Looks teilen sich alle Vibes – bewusst einfach gehalten.
LOOKS = {
    "Goth Baddie": "dunkel",
    "Clean-Girl-Aesthetic": "clean", "Japandi-Ruhepol": "clean",
    "Streetwear-Ikone": "street", "Y2K-Icon": "street", "Sporty Spice": "street",
    "Cozy Cloud": "erde", "Boho-Fee": "erde", "Cottagecore-Träumerei": "erde",
    "Vintage Soul": "erde",
    "Coquette-Darling": "romantisch", "Old-Money-Eleganz": "romantisch",
}

# Unter diesen Punkten ist kein Vibe deutlich genug -> "Unikat"
MIN_SCORE = 0.15
# Zweiter Vibe wird erwähnt, wenn er mindestens so viel % des besten hat
SECOND_VIBE_SHARE = 0.6


@dataclass
class Vibe:
    title: str
    emoji: str
    terms: dict[str, float]   # Begriff -> Gewicht
    lines: list[str]          # mögliche Sprüche (immer positiv!)


VIBES = [
    Vibe("Goth Baddie", "🖤", {"goth": 3, "grunge": 2, "schwarz": 1.2}, [
        "Dunkel, mysteriös und trotzdem die süßeste Person im Raum. "
        "Sogar meine Karotte will jetzt Schwarz tragen.",
        "Main Character in einem Vampir-Film – und zwar der Vampir, den alle lieben. Iconic.",
        "Du bringst Schwarz zum Leuchten. Ich bin ehrlich ein bisschen eingeschüchtert. Und Fan. 🖤",
    ]),
    Vibe("Clean-Girl-Aesthetic", "🤍",
         {"clean": 2, "minimalistisch": 1.5, "weiß": 0.8, "beige": 0.6}, [
        "Effortless und glowy. Dein Pinterest riecht nach Vanille und guten Entscheidungen.",
        "So aufgeräumt, dass sogar mein Bau neidisch ist. Less is more – und du bist more.",
    ]),
    Vibe("Streetwear-Ikone", "🧢",
         {"streetwear": 2, "oversized": 1.5, "sportlich": 0.5, "utility": 0.5}, [
        "Oversized, aber nie overdressed. Du würdest sogar in einer Karottentüte cool aussehen.",
        "Dein Sneaker-Game ist unbesiegbar. Ich hüpf ab jetzt nur noch in Chunky Sneakers.",
    ]),
    Vibe("Cozy Cloud", "☁️", {"cozy": 2, "beige": 0.5, "natur": 0.4}, [
        "Du bist eine warme Decke in Menschenform. Darf ich mich dazukuscheln?",
        "Tee, Strick und Herbstlicht – dein Pinterest ist eine einzige Umarmung.",
    ]),
    Vibe("Old-Money-Eleganz", "💸", {"klassisch": 2, "elegant": 1.5, "braun": 0.3}, [
        "Du siehst aus, als hättest du ein Pferd namens Sir Reginald. "
        "Zeitlos und edel – und wir finden's trotzdem günstig. 😉",
        "Klassisch, edel, zeitlos. Ich trag ab heute nur noch Kaschmir-Ohrenwärmer.",
    ]),
    Vibe("Vintage Soul", "📼", {"vintage": 2, "braun": 0.3}, [
        "Du warst schon cool, bevor es cool war. Wahrscheinlich in den 70ern. Mit Schlaghose.",
        "Thrift-Legende! Jedes Teil hat eine Geschichte – und deine ist die beste.",
    ]),
    Vibe("Y2K-Icon", "💿", {"y2k": 2.5, "rosa": 0.5}, [
        "Glitzer, Low-Rise und Klapphandy-Energie. Du bist der Grund, warum die 2000er zurück sind.",
        "So Y2K, dass mein Pixel-Fell gerade lila werden will.",
    ]),
    Vibe("Boho-Fee", "🌿", {"boho": 2, "natur": 1, "orange": 0.3}, [
        "Du bist ein Sonnenuntergang auf einem Festival. Barfuß. Mit Blumen im Haar.",
        "Frei, warm und voller Pflanzen. Ich zieh bei dir ein, okay? Ich bring Karotten mit.",
    ]),
    Vibe("Coquette-Darling", "🎀", {"coquette": 3, "romantisch": 1.5, "rosa": 1}, [
        "Schleifen überall und Herzchen in den Augen. Du bist so süß, dass ich Konkurrenz bekomme.",
        "Ballerinas, Rosa, Romantik – du lebst in einem Liebesbrief.",
    ]),
    Vibe("Cottagecore-Träumerei", "🍓", {"cottagecore": 3, "romantisch": 0.5, "natur": 0.5}, [
        "Du backst bestimmt Brot und pflückst Erdbeeren. Ich bring die Karotten fürs Picknick!",
    ]),
    Vibe("Japandi-Ruhepol", "🍵", {"japandi": 2, "skandinavisch": 1.5, "natur": 0.5}, [
        "Holz, Leinen, Ruhe – ich werd schon beim Anschauen entspannt. Im besten Sinne.",
        "Zen-Level: Meister. Sogar mein Hoppeln wird bei dir leiser.",
    ]),
    Vibe("Sporty Spice", "⚡", {"sportlich": 2, "outdoor": 1}, [
        "Immer in Bewegung! Du bist schneller als ich – und ich bin ein Hase.",
    ]),
]

UNIQUE = Vibe("Einzigartiges Unikat", "✨", {}, [
    "Dein Stil passt in keine Schublade – und das ist das Coolste überhaupt.",
    "Ich hab alle meine Hasen-Detektiv-Tricks probiert: Du bist einfach einzigartig. ✨",
])

NO_PINS = Vibe("Noch ein Geheimnis", "🥕", {}, [
    "Verbinde Pinterest und lade ein paar Pins – dann verrate ich dir deinen Vibe!",
])


def score(vibe: Vibe, profile: StyleProfile) -> float:
    return sum(weight * profile.weight(term) for term, weight in vibe.terms.items())


def vibe_check(pins: list[dict], rng: random.Random | None = None) -> dict:
    """Ermittelt den Vibe aus ALLEN Pins (Mode und Wohnen zusammen)."""
    rng = rng or random.Random()
    profile = build_style_profile(pins)

    if profile.pin_count == 0:
        best, second = NO_PINS, None
    else:
        ranked = sorted(VIBES, key=lambda v: score(v, profile), reverse=True)
        best_score = score(ranked[0], profile)
        if best_score < MIN_SCORE:
            best, second = UNIQUE, None
        else:
            best = ranked[0]
            runner_up = ranked[1]
            second = runner_up if score(runner_up, profile) >= SECOND_VIBE_SHARE * best_score \
                else None

    top_terms = [t for t, _ in (profile.styles + profile.colors).most_common(3)]
    return {
        "title": best.title,
        "emoji": best.emoji,
        "text": rng.choice(best.lines),
        "second": f"{second.emoji} {second.title}" if second else None,
        "second_title": second.title if second else None,    # ohne Emoji, für die Karte
        "look": LOOKS.get(best.title, "rosa"),
        "terms": top_terms,
        "colors": [{"name": name, "hex": SWATCHES[name]}
                   for name, _ in profile.colors.most_common(4) if name in SWATCHES],
        "pin_count": profile.pin_count,
    }
