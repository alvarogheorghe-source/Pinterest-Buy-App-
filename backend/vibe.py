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

from backend.matching import StyleProfile, audience, build_style_profile

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
    "Clean Girl": "clean", "Japandi Zen": "clean", "Clean Fit": "clean",
    "Streetwear Icon": "street", "Y2K Baby": "street", "Athleisure Era": "street",
    "Effortless Cool": "street",
    "Cozy Era": "erde", "Festival Boho": "erde", "Cottagecore": "erde", "Thrift Legend": "erde",
    "Gorpcore": "erde",
    "Coquette Era": "romantisch", "Quiet Luxury": "romantisch",
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
    audience: str | None = None  # "damen": nicht vorschlagen, wenn das Board klar Herrenmode zeigt


VIBES = [
    Vibe("Goth Baddie", "🖤", {"goth": 3, "grunge": 2, "schwarz": 1.2}, [
        "Dark, mysteriös und trotzdem die süßeste Aura im Raum. "
        "Sogar meine Karotte trägt jetzt Schwarz. 🖤",
        "It's giving Wednesday Addams – nur mit besserem Outfit. Slay in Schwarz.",
        "Deine Aura: +1000. Mein Mut, dich anzusprechen: −3. Iconic.",
    ]),
    Vibe("Clean Girl", "🤍", {"clean": 2, "minimalistisch": 1.5, "weiß": 0.8, "beige": 0.6}, [
        "Slicked Bun, Glow und null Chaos. Dein Pinterest riecht nach Vanille und guten "
        "Entscheidungen.",
        "That-Girl-Energy: Du stehst um 6 auf und trinkst Matcha. Ich schlaf bis 11 im Bau. "
        "Respekt.",
    ], audience="damen"),
    Vibe("Streetwear Icon", "🧢",
         {"streetwear": 2, "oversized": 1.5, "sportlich": 0.5, "utility": 0.5}, [
        "Certified Drip. Du würdest sogar in einer Karottentüte aussehen wie ein Limited Drop.",
        "Dein Sneaker-Game? Unbesiegbar. Ich hüpf ab jetzt nur noch in Chunky Sneakers.",
    ]),
    Vibe("Cozy Era", "☁️", {"cozy": 2, "beige": 0.5, "natur": 0.4}, [
        "Du bist eine warme Decke in Menschenform. Lowkey will ich mich dazukuscheln.",
        "Strick, Tee, Kerzenlicht – it's giving Sonntag im Herbst. Für immer.",
    ]),
    Vibe("Quiet Luxury", "💸", {"klassisch": 2, "elegant": 1.5, "braun": 0.3}, [
        "Kein Logo, aber alle wissen Bescheid. Du siehst aus, als hättest du ein Pferd "
        "namens Sir Reginald.",
        "Old-Money-Aura, Smart-Shopping-Budget. Wir verraten's niemandem. 🤫",
    ]),
    Vibe("Thrift Legend", "📼", {"vintage": 2, "braun": 0.3}, [
        "Du warst schon vintage, bevor es cool war. Jedes Teil hat eine Story – deine ist "
        "die beste.",
        "Second-Hand-Schatzsuche auf Profi-Level. Ich buddel ab jetzt nur noch nach "
        "Vintage-Karotten.",
    ]),
    Vibe("Y2K Baby", "💿", {"y2k": 2.5, "rosa": 0.5}, [
        "Glitzer, Low-Rise und Klapphandy-Energie. Du bist der Grund, warum die 2000er "
        "zurück sind.",
        "So Y2K, dass mein Pixel-Fell gerade Glitzer bekommt. That's hot. 💿",
    ]),
    Vibe("Festival Boho", "🌿", {"boho": 2, "natur": 1, "orange": 0.3}, [
        "Sonnenuntergang, Festival, Blumen im Haar – du bist der Vibe, den alle filmen.",
        "Free Spirit, warmes Herz, viele Pflanzen. Ich zieh bei dir ein, okay? Karotten "
        "bring ich mit.",
    ]),
    Vibe("Coquette Era", "🎀", {"coquette": 3, "romantisch": 1.5, "rosa": 1}, [
        "Schleifen überall und Herzchen in den Augen. So süß, dass ich Konkurrenz bekomme.",
        "Ballerinas, Rosa, Spitze – du lebst in einem Liebesbrief. Delulu? Nein: dreamy.",
    ], audience="damen"),
    Vibe("Cottagecore", "🍓", {"cottagecore": 3, "romantisch": 0.5, "natur": 0.5}, [
        "Du backst bestimmt Sauerteigbrot und pflückst Erdbeeren. Ich bring die Karotten "
        "fürs Picknick!",
        "Main Character in einem Ghibli-Film – und ich wäre dein kleiner Hasen-Sidekick. 🍓",
    ]),
    Vibe("Japandi Zen", "🍵", {"japandi": 2, "skandinavisch": 1.5, "natur": 0.5}, [
        "Holz, Leinen, Ruhe. Schon beim Anschauen sinkt mein Puls – im besten Sinne.",
        "Zen-Level: Meister. Sogar mein Hoppeln wird bei dir leiser.",
    ]),
    Vibe("Athleisure Era", "⚡", {"sportlich": 2, "outdoor": 0.3}, [
        "Pilates um 7, Matcha um 8, Slay den ganzen Tag. Du bist schneller als ich – und "
        "ich bin ein Hase.",
        "Leggings, Sneaker, Energie für drei. Gym-Fit, aber make it fashion.",
    ]),
    Vibe("Gorpcore", "🏔️", {"outdoor": 2, "utility": 0.8}, [
        "Du siehst aus, als würdest du gleich einen Berg besteigen – und danach in den "
        "Coffee Shop. Gorpcore Royalty.",
        "Funktionsjacke, aber fashion. Ich hab nur mein Fell, bin aber trotzdem inspiriert.",
    ]),
]

# Neutral – passen zu jedem Board, z.B. lässige Herrenmode mit Baggy Jeans
VIBES += [
    Vibe("Effortless Cool", "👟", {"casual": 2, "oversized": 0.8, "utility": 0.4}, [
        "Baggy Jeans, gute Laune, null Stress. Du siehst zufällig so cool aus – und genau "
        "das ist die Kunst.",
        "Model-off-Duty-Energy: Fünf Minuten angezogen und trotzdem wie aus dem Lookbook.",
    ]),
    Vibe("Clean Fit", "🤍", {"minimalistisch": 2, "clean": 1, "klassisch": 0.5,
                             "schwarz": 0.4, "weiß": 0.4, "grau": 0.4}, [
        "Wenige Teile, alle perfekt. Dein Kleiderschrank ist aufgeräumter als mein Bau.",
        "Basics auf Level 100. Schlicht ist das neue Laut – you understood the assignment.",
    ]),
]

UNIQUE = Vibe("Main Character", "✨", {}, [
    "Dein Stil passt in keine Schublade – Main-Character-Energy, ganz klar.",
    "Ich hab alle Hasen-Detektiv-Tricks probiert: Du bist dein eigener Trend. ✨",
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
        # Zeigt das Board klar Herrenmode, passen z.B. "Clean Girl" oder "Coquette" nicht
        who = audience(pins)
        candidates = [v for v in VIBES if not (v.audience and who and v.audience != who)]
        ranked = sorted(candidates, key=lambda v: score(v, profile), reverse=True)
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
