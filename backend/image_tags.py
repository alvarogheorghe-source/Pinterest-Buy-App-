"""Was ist auf dem Pin-Bild? Stil und Art (z.B. "goth" + "Jacken") per FashionCLIP.

Viele Pins haben kaum Text – dann findet die Wortsuche (matching.py) nichts. CLIP kann aber
Bilder mit Beschreibungen vergleichen ("Zero-Shot"): Wir geben eine Liste von Sätzen vor
("a photo of goth dark aesthetic fashion", "a photo of a jacket or coat" …) und schauen,
welche am besten zum Bild passen. Die Gewinner landen als Begriffe am Pin:

    pin["image_styles"]     = ["goth"]
    pin["image_categories"] = ["Jacken"]          # bis zu 2 (Outfit-Fotos zeigen mehrere Teile)
    pin["image_gender"]     = "damen"             # nur bei Mode: "herren", "damen" oder None
    pin["image_brands"]     = ["Adidas Samba"]    # nur sehr sichere Treffer (brands.py)
    pin["image_relevant"]   = True                # Vorprüfung: Mode oder Wohnen zu sehen?

Vorprüfung zuerst: Zeigt das Bild Kleidung/Schuhe/Accessoires (Mode), Einrichtung (Wohnen)
oder etwas anderes (Bildschirm, Text, Essen, Landschaft …)? Nur bei Mode/Wohnen wird
weiter erkannt – und die Kategorie nur aus dieser Welt gewählt.
Jeder Begriff wird mit mehreren Sätzen beschrieben (TEMPLATES) und gemittelt – das macht
CLIP spürbar zuverlässiger.

matching.build_style_profile() zählt sie wie Wörter aus dem Pin-Text – so funktionieren
Stilprofil, Vibe-Check und die Suche bei eBay/Etsy auch bei Pins ohne Text.

Läuft automatisch mit:              python -m backend.vision
Ergebnis pro Pin ansehen:           python -m backend.image_tags
"""

import math

from backend import storage
from backend.brands import BRANDS, NO_BRAND_PROMPTS
from backend.matching import CATEGORY_SYNONYMS
from backend.vision import cosine

# Mehrere Formulierungen pro Begriff, gemittelt ("Prompt-Ensemble")
TEMPLATES = ["a photo of {}", "a close-up photo of {}", "a picture of {}"]

# Stil -> Beschreibung auf Englisch (CLIP versteht Englisch am besten)
STYLE_PROMPTS = {
    "streetwear": "streetwear fashion", "oversized": "an oversized baggy outfit",
    "y2k": "y2k 2000s fashion", "casual": "a casual everyday outfit",
    "sportlich": "a sporty athleisure outfit", "romantisch": "a romantic feminine floral look",
    "utility": "a cargo utility outfit", "outdoor": "an outdoor hiking gorpcore outfit",
    "sommer": "a summer outfit", "winter": "a winter outfit",
    "minimalistisch": "a minimalist look", "clean": "the clean girl aesthetic",
    "vintage": "vintage retro clothes or furniture", "elegant": "an elegant chic look",
    "klassisch": "classic old money style", "boho": "boho bohemian style",
    "cozy": "a cozy hygge look", "skandinavisch": "a scandinavian interior",
    "japandi": "a japandi interior", "industrial": "an industrial loft interior",
    "modern": "a modern contemporary interior", "natur": "natural materials like wood, rattan and linen",
    "goth": "goth dark aesthetic fashion", "grunge": "grunge fashion",
    "coquette": "the coquette aesthetic with bows and lace", "cottagecore": "the cottagecore aesthetic",
}

# Kategorie -> Beschreibung. Dazu "Sonstiges", damit z.B. ein Essensfoto nicht als "Deko" endet.
CATEGORY_PROMPTS = {
    "Oberteile": "a top, sweater, hoodie or shirt", "Hosen": "pants or jeans",
    "Jacken": "a jacket or coat", "Kleider & Röcke": "a dress or skirt",
    "Schuhe": "shoes or sneakers", "Accessoires": "a bag, jewelry or accessory",
    "Deko": "home decor like a vase or candles", "Leuchten": "a lamp",
    "Textilien": "pillows, blankets or a rug", "Küche & Tisch": "tableware, mugs or plates",
    "Möbel": "furniture like a chair, table or sofa", "Pflanzen & Töpfe": "a house plant in a pot",
    "Wandgestaltung": "wall art or a poster",
}
OTHER_PROMPTS = {
    "_portrait": "a close-up portrait of a face", "_food": "food or a drink",
    "_landscape": "a landscape or nature scene", "_text": "text, a quote or a document",
    "_animal": "an animal", "_screen": "a computer screen, desktop or laptop",
}

# Vorprüfung: Was zeigt das Bild überhaupt? Schlüssel -> (Gruppe, Beschreibung)
GATE_PROMPTS = {
    "outfit": ("mode", "clothing or an outfit"),
    "person": ("mode", "a person wearing an outfit"),
    "shoes": ("mode", "shoes or sneakers"),
    "accessory": ("mode", "a bag, jewelry or accessories"),
    "social": ("mode", "a screenshot of a social media post showing an outfit"),
    "room": ("wohnen", "an interior room with furniture"),
    "decor": ("wohnen", "home decor like a vase, lamp, candle or pillow"),
    "desktop": ("other", "a computer desktop screenshot with icons and windows"),
    "device": ("other", "a laptop, phone, keyboard or electronic device"),
    "text": ("other", "text, a document or a quote"),
    "food": ("other", "food or a drink"),
    "landscape": ("other", "a landscape or a city street without people"),
    "animal": ("other", "an animal"),
    "vehicle": ("other", "a car or vehicle"),
    "meme": ("other", "a meme, cartoon or drawing"),
}

# Herren- oder Damenmode? Nur bei Mode-Pins – für passendere Suchen ("Herren Baggy Jeans")
GENDER_PROMPTS = {"herren": "menswear, a man wearing the outfit",
                  "damen": "womenswear, a woman wearing the outfit"}

# CLIP-Werte liegen eng beieinander; mit diesem Faktor (wie im CLIP-Modell) werden daraus
# Wahrscheinlichkeiten, die sich klar unterscheiden.
LOGIT_SCALE = 100.0
STYLE_MIN = 0.30          # Stil zählt ab 30 % Wahrscheinlichkeit
SECOND_STYLE_MIN = 0.20   # ein zweiter Stil ab 20 %
CATEGORY_MIN = 0.40       # Kategorie ab 40 % (und nur, wenn nicht "Sonstiges" gewinnt)
SECOND_CATEGORY_MIN = 0.25  # zweites Teil im Bild (z.B. Hose UND Oberteil) ab 25 %
GENDER_MIN = 0.70         # Herren/Damen nur, wenn ziemlich eindeutig
BRAND_MIN = 0.60          # Marke nur, wenn sie klar vor allen anderen UND "keine Marke" liegt
GATE_MIN = 0.50           # Mode + Wohnen zusammen mind. 50 % – sonst "nichts für Malipin"


def softmax(scores: dict[str, float]) -> dict[str, float]:
    top = max(scores.values())
    exp = {key: math.exp(LOGIT_SCALE * (value - top)) for key, value in scores.items()}
    total = sum(exp.values())
    return {key: value / total for key, value in exp.items()}


def descriptions() -> dict[str, str]:
    """Schlüssel -> Beschreibung, z.B. "style:goth" -> "goth dark aesthetic fashion"."""
    found = {f"style:{k}": v for k, v in STYLE_PROMPTS.items()}
    found.update({f"category:{k}": v for k, v in {**CATEGORY_PROMPTS, **OTHER_PROMPTS}.items()})
    found.update({f"gender:{k}": v for k, v in GENDER_PROMPTS.items()})
    brand_prompts = {name: brand.prompt for name, brand in BRANDS.items()}
    found.update({f"brand:{k}": v for k, v in {**brand_prompts, **NO_BRAND_PROMPTS}.items()})
    found.update({f"gate:{k}": text for k, (_, text) in GATE_PROMPTS.items()})
    return found


def all_prompts() -> dict[str, list[str]]:
    """Schlüssel -> alle Sätze, z.B. "style:goth" -> ["a photo of goth …", "a picture of goth …"]."""
    return {key: [t.format(text) for t in TEMPLATES] for key, text in descriptions().items()}


def label_vectors(embedder, store) -> dict[str, list[float]]:
    """Ein Vektor pro Begriff = Mittel seiner Sätze. Einmal berechnet, dann im Speicher."""
    from backend.vision import mean_direction
    prompts = all_prompts()
    missing = [key for key, texts in prompts.items()
               if store.get(f"label:{key}", " | ".join(texts)) is None]
    if missing:
        texts = [text for key in missing for text in prompts[key]]
        vectors = iter(embedder.embed_texts(texts))
        for key in missing:
            group = [next(vectors) for _ in prompts[key]]
            store.put(f"label:{key}", " | ".join(prompts[key]), mean_direction(group))
    return {key: store.get(f"label:{key}") for key in prompts}


def gate(scores: dict[str, float]) -> tuple[bool, str | None, str]:
    """Vorprüfung -> (relevant?, Welt "mode"/"wohnen"/None, stärkster Einzel-Treffer)."""
    probs = softmax(scores)
    groups = {"mode": 0.0, "wohnen": 0.0, "other": 0.0}
    for key, p in probs.items():
        groups[GATE_PROMPTS[key][0]] += p
    relevant = groups["mode"] + groups["wohnen"] >= GATE_MIN
    world = ("mode" if groups["mode"] >= groups["wohnen"] else "wohnen") if relevant else None
    return relevant, world, max(probs, key=probs.get)


def tag(pin_vector: list[float], labels: dict[str, list[float]]) -> dict:
    """Ein Pin-Bild -> {"relevant", "department", "seen", "styles", "categories", "gender", "brands"}"""
    def scores(prefix):
        return {key[len(prefix):]: cosine(pin_vector, vector)
                for key, vector in labels.items() if key.startswith(prefix)}

    relevant, world, seen = gate(scores("gate:"))
    result = {"relevant": relevant, "department": world, "seen": seen,
              "styles": [], "categories": [], "gender": None, "brands": []}
    if not relevant:
        return result   # Bildschirm, Essen, Text … -> keine Stil-Begriffe, keine Suche

    styles = sorted(softmax(scores("style:")).items(), key=lambda kv: -kv[1])
    chosen_styles = [name for name, p in styles[:1] if p >= STYLE_MIN]
    if chosen_styles and len(styles) > 1 and styles[1][1] >= SECOND_STYLE_MIN:
        chosen_styles.append(styles[1][0])

    # Kategorie nur aus der erkannten Welt (+ "Sonstiges"): ein Outfit vor einer Wand
    # wird so nicht zu "Wandgestaltung"
    category_scores = {k: v for k, v in scores("category:").items()
                       if k.startswith("_") or CATEGORY_SYNONYMS[k][0] == world}
    ranked = sorted(softmax(category_scores).items(), key=lambda kv: -kv[1])
    categories = []
    if ranked[0][1] >= CATEGORY_MIN and not ranked[0][0].startswith("_"):
        categories.append(ranked[0][0])
        second, p2 = ranked[1]
        if p2 >= SECOND_CATEGORY_MIN and not second.startswith("_"):
            categories.append(second)

    gender, brands = None, []
    if any(CATEGORY_SYNONYMS[c][0] == "mode" for c in categories):
        name, p = max(softmax(scores("gender:")).items(), key=lambda kv: kv[1])
        gender = name if p >= GENDER_MIN else None
        name, p = max(softmax(scores("brand:")).items(), key=lambda kv: kv[1])
        brands = [name] if p >= BRAND_MIN and not name.startswith("_") else []
    result.update(styles=chosen_styles, categories=categories, gender=gender, brands=brands)
    return result


def tag_pins(embedder, store) -> int:
    """Alle gespeicherten Pins mit Bild-Vektor beschriften. Gibt die Anzahl zurück."""
    data = storage.load_pins()
    labels = label_vectors(embedder, store)
    store.save()
    tagged = 0
    for pin in data["pins"]:
        vector = store.get(f"pin:{pin['id']}")
        if not vector:
            continue
        result = tag(vector, labels)
        pin["image_styles"], pin["image_categories"] = result["styles"], result["categories"]
        pin["image_gender"] = result["gender"]
        pin["image_brands"] = result["brands"]
        pin["image_relevant"] = result["relevant"]
        tagged += 1
    if tagged:
        storage.save_pins(data)   # leert auch den eBay/Etsy-Zwischenspeicher (neues Profil)
    return tagged


def main() -> None:
    """Zeigt, was auf jedem Pin-Bild erkannt wurde."""
    pins = storage.load_pins()["pins"]
    tagged = [pin for pin in pins if "image_styles" in pin]
    if not tagged:
        print("Noch keine Bild-Begriffe – zuerst ausführen:  python -m backend.vision")
        return
    for pin in tagged:
        text = (pin.get("title") or pin.get("description") or "(ohne Text)")[:45]
        found = (pin["image_styles"] + pin["image_categories"] + [pin.get("image_gender") or ""]
                 + pin.get("image_brands", []))
        found = [f for f in found if f]
        if pin.get("image_relevant") is False:
            found = ["(keine Mode/Wohnen – zählt nicht)"]
        print(f"{text:<47} -> {', '.join(found) or '–'}")
    print(f"\n{len(tagged)} Pins mit Bild-Begriffen.")


if __name__ == "__main__":
    main()
