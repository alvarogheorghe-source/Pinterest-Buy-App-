"""Was ist auf dem Pin-Bild? Stil und Art (z.B. "goth" + "Jacken") per FashionCLIP.

Viele Pins haben kaum Text – dann findet die Wortsuche (matching.py) nichts. CLIP kann aber
Bilder mit Beschreibungen vergleichen ("Zero-Shot"): Wir geben eine Liste von Sätzen vor
("a photo of goth dark aesthetic fashion", "a photo of a jacket or coat" …) und schauen,
welche am besten zum Bild passen. Die Gewinner landen als Begriffe am Pin:

    pin["image_styles"]     = ["goth"]
    pin["image_categories"] = ["Jacken"]

matching.build_style_profile() zählt sie wie Wörter aus dem Pin-Text – so funktionieren
Stilprofil, Vibe-Check und die Suche bei eBay/Etsy auch bei Pins ohne Text.

Läuft automatisch mit:              python -m backend.vision
Ergebnis pro Pin ansehen:           python -m backend.image_tags
"""

import math

from backend import storage
from backend.vision import cosine

TEMPLATE = "a photo of {}"

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
    "_landscape": "a landscape or nature scene", "_text": "text, a quote or a screenshot",
    "_animal": "an animal",
}

# CLIP-Werte liegen eng beieinander; mit diesem Faktor (wie im CLIP-Modell) werden daraus
# Wahrscheinlichkeiten, die sich klar unterscheiden.
LOGIT_SCALE = 100.0
STYLE_MIN = 0.30          # Stil zählt ab 30 % Wahrscheinlichkeit
SECOND_STYLE_MIN = 0.20   # ein zweiter Stil ab 20 %
CATEGORY_MIN = 0.40       # Kategorie ab 40 % (und nur, wenn nicht "Sonstiges" gewinnt)


def softmax(scores: dict[str, float]) -> dict[str, float]:
    top = max(scores.values())
    exp = {key: math.exp(LOGIT_SCALE * (value - top)) for key, value in scores.items()}
    total = sum(exp.values())
    return {key: value / total for key, value in exp.items()}


def all_prompts() -> dict[str, str]:
    """Schlüssel im Speicher -> vollständiger Satz, z.B. "style:goth" -> "a photo of goth …"."""
    prompts = {f"style:{k}": TEMPLATE.format(v) for k, v in STYLE_PROMPTS.items()}
    prompts.update({f"category:{k}": TEMPLATE.format(v)
                    for k, v in {**CATEGORY_PROMPTS, **OTHER_PROMPTS}.items()})
    return prompts


def label_vectors(embedder, store) -> dict[str, list[float]]:
    """Vektoren der Sätze – einmal berechnet, dann im Speicher (data/embeddings.json)."""
    prompts = all_prompts()
    missing = [key for key, text in prompts.items() if store.get(f"label:{key}", text) is None]
    if missing:
        vectors = embedder.embed_texts([prompts[key] for key in missing])
        for key, vector in zip(missing, vectors):
            store.put(f"label:{key}", prompts[key], vector)
    return {key: store.get(f"label:{key}") for key in prompts}


def tag(pin_vector: list[float], labels: dict[str, list[float]]) -> dict[str, list[str]]:
    """Ein Pin-Bild -> {"styles": [...], "categories": [...]}"""
    def scores(prefix):
        return {key[len(prefix):]: cosine(pin_vector, vector)
                for key, vector in labels.items() if key.startswith(prefix)}

    styles = sorted(softmax(scores("style:")).items(), key=lambda kv: -kv[1])
    chosen_styles = [name for name, p in styles[:1] if p >= STYLE_MIN]
    if chosen_styles and len(styles) > 1 and styles[1][1] >= SECOND_STYLE_MIN:
        chosen_styles.append(styles[1][0])

    category, p = max(softmax(scores("category:")).items(), key=lambda kv: kv[1])
    categories = [category] if p >= CATEGORY_MIN and not category.startswith("_") else []
    return {"styles": chosen_styles, "categories": categories}


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
        found = pin["image_styles"] + pin["image_categories"]
        print(f"{text:<47} -> {', '.join(found) or '–'}")
    print(f"\n{len(tagged)} Pins mit Bild-Begriffen.")


if __name__ == "__main__":
    main()
