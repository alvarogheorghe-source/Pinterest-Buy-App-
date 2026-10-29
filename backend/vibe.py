"""Malis Vibe-Check: Welchen Vibe gibt dein Pinterest ab? Immer positiv!

Jeder Vibe hat Begriffe (Stile, Farben) mit Gewichten. Wir rechnen für jeden Vibe:
    Punkte = Summe( Gewicht × Anteil der Pins mit diesem Begriff )
Der Vibe mit den meisten Punkten gewinnt. Ist ein zweiter fast so stark, kommt er
als "mit einer Prise …" dazu. Die Sprüche werden zufällig gewählt, damit Mali
bei jedem Klick etwas Neues sagt.

Neue Vibes oder Sprüche? Einfach unten in VIBES ergänzen.
"""

import random
import re
from dataclasses import dataclass

from backend.i18n import tr
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
    Vibe("Goth Baddie", "", {"goth": 3, "grunge": 2, "schwarz": 1.2}, [
        "Dark, mysteriös und trotzdem die süßeste Aura im Raum. "
        "Sogar meine Karotte trägt jetzt Schwarz.",
        "It's giving Wednesday Addams, nur mit besserem Outfit. Slay in Schwarz.",
        "Deine Aura: +1000. Mein Mut, dich anzusprechen: −3. Iconic.",
        "Du trägst nicht Schwarz, Schwarz trägt dich. Ich bin ein bisschen eingeschüchtert. Und Fan.",
        "Mondlicht, Silberschmuck, Main-Character-Energy. Ich hoppel ab heute nur noch nachts.",
    ]),
    Vibe("Clean Girl", "🤍", {"clean": 2, "minimalistisch": 1.5, "weiß": 0.8, "beige": 0.6}, [
        "Slicked Bun, Glow und null Chaos. Dein Pinterest riecht nach Vanille und guten "
        "Entscheidungen.",
        "That-Girl-Energy. Du stehst um 6 auf und trinkst Matcha, ich schlaf bis 11 im Bau. Respekt.",
        "Gold Hoops, Lip Oil, Leinenhose. Du siehst aus wie ein Sonntagmorgen in Kopenhagen.",
        "So effortless, dass es fast unfair ist. Ich hab mir gerade auch die Ohren gegelt. 🤍",
        "Dein Feed ist so clean, ich will darin meditieren. Dein Glow ist unbezahlbar.",
    ], audience="damen"),
    Vibe("Streetwear Icon", "🧢",
         {"streetwear": 2, "oversized": 1.5, "sportlich": 0.5, "utility": 0.5}, [
        "Certified Drip. Du würdest sogar in einer Karottentüte aussehen wie ein Limited Drop.",
        "Dein Sneaker-Game? Unbesiegbar. Ich hüpf ab jetzt nur noch in Chunky Sneakers.",
        "Du stehst nicht in der Drop-Schlange, du BIST der Drop. 🔥",
        "Hoodie, Cap, Attitude. Ich trag meine Ohren ab heute nur noch backwards.",
        "Fit Check bestanden mit 11 von 10. Die Straße ist offiziell dein Laufsteg.",
    ]),
    Vibe("Cozy Era", "☁️", {"cozy": 2, "beige": 0.5, "natur": 0.4}, [
        "Du bist eine warme Decke in Menschenform. Lowkey will ich mich dazukuscheln.",
        "Strick, Tee, Kerzenlicht. It's giving Sonntag im Herbst, für immer.",
        "Oversized Strick und ein Buch im Bett. Du hast das Geheimnis des Lebens gelöst.",
        "Maximal hygge. Ich roll mich jetzt in deinem Feed zusammen und schlaf ein. ☁️",
        "Du bist das Gefühl von frischen Socken aus dem Trockner. Ganz großes Kino.",
    ]),
    Vibe("Quiet Luxury", "💸", {"klassisch": 2, "elegant": 1.5, "braun": 0.3}, [
        "Kein Logo, aber alle wissen Bescheid. Du siehst aus, als hättest du ein Pferd "
        "namens Sir Reginald.",
        "Old-Money-Aura, Smart-Shopping-Budget. Wir verraten's niemandem. 🤫",
        "Kaschmir, Loafers, leise Eleganz. Du redest nicht über Stil, du hast ihn einfach.",
        "Du siehst aus, als würdest du im Sommer „nur kurz“ nach Capri fliegen. Mit Handgepäck.",
        "Zeitlos und edel. Ich trag ab heute nur noch Kaschmir-Ohrenwärmer. Diskret natürlich.",
    ]),
    Vibe("Thrift Legend", "📼", {"vintage": 2, "braun": 0.3}, [
        "Du warst schon vintage, bevor es cool war. Jedes Teil hat eine Story und deine ist die beste.",
        "Second-Hand-Schatzsuche auf Profi-Level. Ich buddel ab jetzt nur noch nach "
        "Vintage-Karotten.",
        "Andere gehen shoppen, du gehst auf Schatzsuche. Und gewinnst jedes Mal. 📼",
        "Dein Kleiderschrank hat mehr Geschichte als mein Bau. Und mein Bau ist SEHR alt.",
        "Nachhaltig, einzigartig, unbezahlbar. Und trotzdem für 8 € vom Flohmarkt. Legendär.",
    ]),
    Vibe("Y2K Baby", "💿", {"y2k": 2.5, "rosa": 0.5}, [
        "Glitzer, Low-Rise und Klapphandy-Energie. Du bist der Grund, warum die 2000er "
        "zurück sind.",
        "So Y2K, dass mein Pixel-Fell gerade Glitzer bekommt. That's hot. 💿",
        "Butterfly-Clips, Baby Tee, Low-Rise. Du machst die 2000er besser als die 2000er.",
        "Wäre dein Feed ein Klingelton, wäre er ein absoluter Ohrwurm. Iconic.",
        "Pink, Glitzer und null Kompromisse. Dein Feed ist offiziell ein Throwback-Hit.",
    ]),
    Vibe("Festival Boho", "🌿", {"boho": 2, "natur": 1, "orange": 0.3}, [
        "Sonnenuntergang, Festival, Blumen im Haar. Du bist der Vibe, den alle filmen.",
        "Free Spirit, warmes Herz, viele Pflanzen. Ich zieh bei dir ein, okay? Karotten "
        "bring ich mit.",
        "Fransen, Leinen und Good Vibes only. Du riechst bestimmt nach Sonnencreme und Freiheit.",
        "Barfuß im Gras, Blumen im Haar. Du bist der Golden-Hour-Filter in Menschenform.",
        "So free, dass mein Hasenherz mitschwingt. Nimmst du mich mit aufs nächste Festival? 🌿",
    ]),
    Vibe("Coquette Era", "🎀", {"coquette": 3, "romantisch": 1.5, "rosa": 1}, [
        "Schleifen überall und Herzchen in den Augen. So süß, dass ich Konkurrenz bekomme.",
        "Ballerinas, Rosa, Spitze. Du lebst in einem Liebesbrief. Delulu? Nein, dreamy.",
        "Du hast mehr Schleifen als ich Karotten. Und ich hab SEHR viele Karotten. 🎀",
        "Lana Del Rey auf Repeat und Herzchen in den Augen. So romantisch, das ist filmreif.",
        "So soft und so süß, mein Pixel-Herz macht gerade Purzelbäume.",
    ], audience="damen"),
    Vibe("Cottagecore", "🍓", {"cottagecore": 3, "romantisch": 0.5, "natur": 0.5}, [
        "Du backst bestimmt Sauerteigbrot und pflückst Erdbeeren. Ich bring die Karotten "
        "fürs Picknick!",
        "Main Character in einem Ghibli-Film, und ich wäre dein kleiner Hasen-Sidekick. 🍓",
        "Leinenkleid, Weidenkorb, Wildblumen. Dein Feed ist ein Sonntag auf dem Land.",
        "Du gibst bestimmt jeder Pflanze einen Namen. Meine heißt übrigens Karotte.",
        "Slow Living, aber make it aesthetic. Ich bleib noch zum Teetrinken, okay?",
    ]),
    Vibe("Japandi Zen", "🍵", {"japandi": 2, "skandinavisch": 1.5, "natur": 0.5}, [
        "Holz, Leinen, Ruhe. Schon beim Anschauen sinkt mein Puls, im besten Sinne.",
        "Zen auf Meister-Level. Sogar mein Hoppeln wird bei dir leiser.",
        "Weniger Zeug, mehr Ruhe. Dein Zuhause sieht aus wie tiefes Durchatmen.",
        "Clean Lines, warme Hölzer. So ruhig, dass ich mein Hoppeln auf Flüstern stelle.",
        "Wabi-Sabi-Energy. Du findest Schönheit im Unperfekten, ich bin offiziell inspiriert. 🍵",
    ]),
    Vibe("Athleisure Era", "⚡", {"sportlich": 2, "outdoor": 0.3}, [
        "Pilates um 7, Matcha um 8, Slay den ganzen Tag. Du bist schneller als ich, und ich bin ein Hase.",
        "Leggings, Sneaker, Energie für drei. Gym-Fit, aber make it fashion.",
        "Vom Gym direkt ins Café und trotzdem die best-dressed Person im Raum. Wie?!",
        "Deine Workout-Fits haben mehr Stil als manche Hochzeitsoutfits. Respekt.",
        "Hoodie, Leggings, Sneaker, Glow. Sogar meine Ohren machen jetzt Stretching. ⚡",
    ]),
    Vibe("Gorpcore", "🏔️", {"outdoor": 2, "utility": 0.8}, [
        "Du siehst aus, als würdest du gleich einen Berg besteigen und danach in den Coffee Shop gehen. Gorpcore Royalty.",
        "Funktionsjacke, aber fashion. Ich hab nur mein Fell, bin aber trotzdem inspiriert.",
        "Wasserdicht, winddicht, stylisch. Du bist bereit für jedes Wetter und jedes Foto.",
        "Trail-Sneaker an den Füßen, Abenteuer im Herzen. Ich pack schon mal Karotten-Snacks ein.",
        "Outdoor-Look, Großstadt-Energy. Ob Gipfel oder Montagmorgen, du rockst beides. 🏔️",
    ]),
]

# Neutral – passen zu jedem Board, z.B. lässige Herrenmode mit Baggy Jeans
VIBES += [
    Vibe("Effortless Cool", "👟", {"casual": 2, "oversized": 0.8, "utility": 0.4}, [
        "Baggy Jeans, gute Laune, null Stress. Du siehst zufällig so cool aus, und genau das ist die Kunst.",
        "Model-off-Duty-Energy. Fünf Minuten angezogen und trotzdem wie aus dem Lookbook.",
        "Zwei Minuten anziehen und besser aussehen als ich nach einer Stunde Fellpflege. Wie?!",
        "Nonchalant, entspannt, unbothered. Deine Aura sagt einfach „ich hab's drauf“.",
        "Weite Jeans, weißes Tee, null Stress. Die einfachste Formel, perfekt umgesetzt. 👟",
    ]),
    Vibe("Clean Fit", "🤍", {"minimalistisch": 2, "clean": 1, "klassisch": 0.5,
                             "schwarz": 0.4, "weiß": 0.4, "grau": 0.4}, [
        "Wenige Teile, alle perfekt. Dein Kleiderschrank ist aufgeräumter als mein Bau.",
        "Basics auf Level 100. Schlicht ist das neue Laut, you understood the assignment.",
        "Schwarz, Weiß, Grau, und trotzdem drehen sich alle um. Das ist Kunst.",
        "Kein Chaos, nur Qualität. Dein Outfit sieht aus wie ein perfekt sortierter Feed.",
        "Minimal, aber nie basic. Ich hab sofort meinen Bau entrümpelt. 🤍",
    ]),
]

UNIQUE = Vibe("Main Character", "✨", {}, [
    "Dein Stil passt in keine Schublade. Main-Character-Energy, ganz klar.",
    "Ich hab alle Hasen-Detektiv-Tricks probiert. Du bist dein eigener Trend. ✨",
    "Kein Trend kann dich einfangen, du erfindest einfach deinen eigenen.",
    "Ich hab in meinem Vibe-Buch nachgeschaut. Für dich gibt's noch keinen Namen. Iconic.",
    "Ein bisschen von allem, ganz viel von dir. Genau so geht persönlicher Stil.",
])

NO_PINS = Vibe("Noch ein Geheimnis", "🥕", {}, [
    "Verbinde Pinterest und lade ein paar Pins, dann verrate ich dir deinen Vibe!",
])


# --- Malis Outfit auf der Vibe-Karte: aus den Pins zusammengesetzt ----------------------------
# Oberteil nach Stil/Kategorie, Farbe aus der häufigsten Pin-Farbe, bis zu 2 Accessoires.
GARMENT_BY_STYLE = [
    ({"coquette", "cottagecore", "romantisch"}, "dress"), ({"elegant", "klassisch"}, "blazer"),
    ({"cozy", "winter"}, "knit"), ({"goth", "grunge", "utility", "outdoor"}, "jacket"),
    ({"streetwear", "sportlich", "oversized"}, "hoodie"),
]
GARMENT_BY_CATEGORY = {"Kleider&Röcke": "dress", "Jacken": "jacket"}
ACCESSORY_BY_STYLE = [
    ("goth", "choker"), ("grunge", "choker"), ("coquette", "bow"), ("romantisch", "bow"),
    ("y2k", "sunglasses"), ("streetwear", "sunglasses"), ("cottagecore", "flowers"), ("boho", "flowers"),
    ("elegant", "pearls"), ("klassisch", "pearls"), ("cozy", "scarf"), ("winter", "beanie"),
    ("outdoor", "beanie"), ("sportlich", "headband"), ("clean", "hairclip"),
    ("minimalistisch", "hairclip"), ("vintage", "glasses"),
]
NOT_FOR_CLOTHES = {"gold", "silber"}


def _darker(hex_color: str, factor: float = 0.78) -> str:
    n = int(hex_color[1:], 16)
    r, g, b = (int(((n >> s) & 255) * factor) for s in (16, 8, 0))
    return f"#{r:02x}{g:02x}{b:02x}"


def outfit(profile: StyleProfile) -> dict:
    styles = profile.styles
    categories = {c: n for c, n in profile.categories.items() if c in GARMENT_BY_CATEGORY}
    garment = "tee"
    best_style = max((sum(styles[s] for s in group), kind) for group, kind in GARMENT_BY_STYLE)
    best_cat = max(((n, GARMENT_BY_CATEGORY[c]) for c, n in categories.items()), default=(0, "tee"))
    if max(best_style[0], best_cat[0]) > 0:
        garment = best_style[1] if best_style[0] >= best_cat[0] else best_cat[1]
    colors = [c for c, _ in profile.colors.most_common() if c in SWATCHES and c not in NOT_FOR_CLOTHES]
    main = SWATCHES[colors[0]] if colors else "#e8b4bc"
    accent = SWATCHES[colors[1]] if len(colors) > 1 else _darker(main, 0.6)
    accessories = []
    for style, acc in sorted(ACCESSORY_BY_STYLE, key=lambda sa: -styles[sa[0]]):
        if styles[style] and acc not in accessories:
            accessories.append(acc)
    if profile.colors["gold"] > profile.colors["silber"] and profile.colors["gold"]:
        accessories.append("goldchain")
    elif profile.colors["silber"]:
        accessories.append("silverchain")
    if profile.categories["Accessoires"] and "bag" not in accessories:
        accessories.append("bag")
    boots = styles["goth"] + styles["grunge"] > 0
    return {"garment": garment, "color": main, "shade": _darker(main), "accent": accent,
            "shoes": "#2b2228" if boots else "#fbfaf7", "accessories": accessories[:2]}


def slug(text: str) -> str:
    """"Goth Baddie" -> "goth-baddie" (für Links ins Stil-Lexikon, style_guide.py)."""
    text = text.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def score(vibe: Vibe, profile: StyleProfile) -> float:
    return sum(weight * profile.weight(term) for term, weight in vibe.terms.items())


def vibe_check(pins: list[dict], rng: random.Random | None = None, avoid: str | None = None) -> dict:
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
    lines = [tr(line) for line in best.lines]          # in der Sprache der Person
    return {
        "title": tr(best.title),
        "emoji": best.emoji,
        # "Anderer Spruch": nie zweimal hintereinander derselbe (avoid = der letzte)
        "text": rng.choice([line for line in lines if line != avoid] or lines),
        "second": f"{second.emoji} {tr(second.title)}".strip() if second else None,
        "second_title": tr(second.title) if second else None,    # ohne Emoji, für die Karte
        "look": LOOKS.get(best.title, "rosa"),
        # Link ins Stil-Lexikon (/stile.html#vibe-goth-baddie) – nicht für "Noch ein Geheimnis"
        "slug": None if best is NO_PINS else "vibe-" + slug(best.title),
        "terms": [tr(term) for term in top_terms],
        "colors": [{"name": tr(name), "hex": SWATCHES[name]}
                   for name, _ in profile.colors.most_common(4) if name in SWATCHES],
        "pin_count": profile.pin_count,
        # Für die Vibe-Karte: Eigenschaften, Superkraft, Signature-Piece, passender Vibe
        **_card_profile(best.title, second),
        "outfit": outfit(profile) if profile.pin_count else None,
    }


def _card_profile(title: str, second: Vibe | None) -> dict:
    from backend import i18n, vibe_profiles
    lang = i18n.current()
    data = vibe_profiles.profile(title, lang)
    if not data:
        return {"traits": [], "power": None, "piece": None, "duo": None}
    duo = data["duo"]
    return {"traits": data["traits"], "power": data["power"], "piece": data["piece"],
            "duo": tr(duo) if duo else None}
