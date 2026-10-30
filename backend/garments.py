"""Kleidungsstücke auf einem Foto finden und ausschneiden.

FashionCLIP (vision.py) sieht immer das GANZE Bild: Person, Hintergrund und alle Teile auf
einmal. Bei einem Straßenfoto rät es dann, welches Teil gemeint ist, und die Hauptfarbe ist
oft die Wand oder Wiese. Darum vorher ein Erkennungs-Modell, das trainiert ist, einzelne
Kleidungsstücke zu finden (Kasten um Jacke, Hose, Schuhe …). Jeder Ausschnitt sieht dann
fast wie ein Produktfoto aus und wird einzeln gesucht, mit eigener Farbe.

Modell: YOLOS, trainiert auf Fashionpedia (ca. 120 MB, läuft auf der CPU). Ein anderes Modell
geht mit GARMENT_MODEL=... in .env, solange es die Teile mit Namen wie unten benennt.
Ohne KI-Pakete oder wenn das Modell nicht lädt: find() liefert [] und alles läuft wie bisher.
"""

import io
import logging
import os
import threading
from dataclasses import dataclass

DEFAULT_MODEL = "valentinafeve/yolos-fashionpedia"
# Manche Modelle bringen keine Bild-Vorverarbeitung mit -> die vom Basis-Modell nehmen
FALLBACK_PROCESSOR = "hustvl/yolos-small"

MIN_SCORE = 0.5      # so sicher muss das Modell sein
MIN_AREA = 0.015     # Ausschnitt mindestens 1,5 % des Bildes (keine winzigen Uhren o.ä.)
# Schuhe und Taschen sind auf Ganzkörperfotos klein – die dürfen kleiner sein
SMALL_AREA = {"Schuhe": 0.003, "Accessoires": 0.005}
MAX_PIECES = 4       # höchstens so viele Teile pro Foto suchen
PADDING = 0.06       # etwas Rand um den Kasten, damit das Teil ganz drauf ist

# Fashionpedia-Klassen in der Reihenfolge des Modells (falls es nur "LABEL_7" sagt)
FASHIONPEDIA = [
    "shirt, blouse", "top, t-shirt, sweatshirt", "sweater", "cardigan", "jacket", "vest",
    "pants", "shorts", "skirt", "coat", "dress", "jumpsuit", "cape", "glasses", "hat",
    "headband, head covering, hair accessory", "tie", "glove", "watch", "belt", "leg warmer",
    "tights, stockings", "sock", "shoe", "bag, wallet", "scarf", "umbrella", "hood", "collar",
    "lapel", "epaulette", "sleeve", "pocket", "neckline", "buckle", "zipper", "applique",
    "bead", "bow", "flower", "fringe", "ribbon", "rivet", "ruffle", "sequin", "tassel",
]

# Teil -> unsere Kategorie (matching.CATEGORY_SYNONYMS). Was fehlt (Ärmel, Taschen,
# Reißverschluss …), wird nicht gesucht.
CATEGORY = {
    "shirt, blouse": "Oberteile", "top, t-shirt, sweatshirt": "Oberteile",
    "sweater": "Oberteile", "cardigan": "Oberteile", "vest": "Oberteile",
    "jacket": "Jacken", "coat": "Jacken", "cape": "Jacken",
    "pants": "Hosen", "shorts": "Hosen",
    "skirt": "Kleider & Röcke", "dress": "Kleider & Röcke", "jumpsuit": "Kleider & Röcke",
    "shoe": "Schuhe", "bag, wallet": "Accessoires", "hat": "Accessoires", "scarf": "Accessoires",
    # gröbere Modelle benennen so
    "top": "Oberteile", "outer": "Jacken", "bottom": "Hosen", "shoes": "Schuhe", "bag": "Accessoires",
}


# Das Modell verwechselt Hoodie, Zip-Hoodie, Jacke und Cardigan leicht – bei uns liegen
# Hoodies aber unter "Oberteile". Darum für den Oberkörper in beiden suchen.
SEARCH = {"Oberteile": ["Oberteile", "Jacken"], "Jacken": ["Jacken", "Oberteile"]}


def search_categories(category: str) -> list[str]:
    return SEARCH.get(category, [category])


@dataclass
class Piece:
    """Ein gefundenes Kleidungsstück: Kategorie, Sicherheit, Kasten (x0, y0, x1, y1) und der
    Ausschnitt als JPEG (nur im Arbeitsspeicher)."""
    category: str
    label: str
    score: float
    box: tuple[int, int, int, int]
    crop: bytes


def label_name(label: str) -> str:
    """"LABEL_6" -> "pants"; echte Namen bleiben."""
    if label.startswith("LABEL_") and label[6:].isdigit() and int(label[6:]) < len(FASHIONPEDIA):
        return FASHIONPEDIA[int(label[6:])]
    return label.strip().lower()


class Detector:
    """Das echte Erkennungs-Modell (transformers "object-detection")."""

    def __init__(self, name: str | None = None):
        from transformers import AutoImageProcessor, pipeline
        self.name = name or os.getenv("GARMENT_MODEL", "").strip() or DEFAULT_MODEL
        try:
            self.pipe = pipeline("object-detection", model=self.name, device=-1)
        except (OSError, ValueError):
            processor = AutoImageProcessor.from_pretrained(FALLBACK_PROCESSOR)
            self.pipe = pipeline("object-detection", model=self.name, device=-1,
                                 image_processor=processor)

    def detect(self, image) -> list[dict]:
        """PIL-Bild -> [{"label", "score", "box": {"xmin", "ymin", "xmax", "ymax"}}]"""
        return self.pipe(image, threshold=MIN_SCORE)


_detector: dict = {}
_lock = threading.Lock()


def get_detector():
    """Einmal laden und behalten. None, wenn es nicht geht (dann ohne Ausschneiden)."""
    with _lock:
        if "model" not in _detector:
            try:
                _detector["model"] = Detector()
            except Exception as err:  # noqa: BLE001  (fehlende Pakete, kein Download …)
                logging.getLogger(__name__).warning("Kleidungs-Erkennung nicht verfügbar: %s", err)
                _detector["model"] = None
        return _detector["model"]


def find(image_bytes: bytes, detector=None) -> list[Piece]:
    """Foto -> die größten erkannten Kleidungsstücke (je Kategorie eins), größtes zuerst."""
    detector = detector or get_detector()
    if detector is None:
        return []
    from PIL import Image
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        found = detector.detect(image)
    except Exception:  # noqa: BLE001  (kaputtes Bild, Modellfehler -> ohne Ausschneiden)
        return []
    width, height = image.size
    best: dict[str, tuple[float, dict, str]] = {}
    for item in found:
        name = label_name(item["label"])
        category = CATEGORY.get(name)
        if not category or item["score"] < MIN_SCORE:
            continue
        box = dict(item["box"])
        if category == "Schuhe" and category in best:
            # Zwei Schuhe -> ein Ausschnitt mit beiden
            other = best[category][1]["box"]
            box = {"xmin": min(box["xmin"], other["xmin"]), "ymin": min(box["ymin"], other["ymin"]),
                   "xmax": max(box["xmax"], other["xmax"]), "ymax": max(box["ymax"], other["ymax"])}
        area = (box["xmax"] - box["xmin"]) * (box["ymax"] - box["ymin"]) / (width * height)
        if area < SMALL_AREA.get(category, MIN_AREA):
            continue
        # Pro Kategorie nur das größte Teil
        if category not in best or area > best[category][0]:
            best[category] = (area, {**item, "box": box}, name)

    pieces = []
    for category, (_, item, name) in sorted(best.items(), key=lambda kv: -kv[1][0])[:MAX_PIECES]:
        b = item["box"]
        pad_x, pad_y = (b["xmax"] - b["xmin"]) * PADDING, (b["ymax"] - b["ymin"]) * PADDING
        box = (max(0, int(b["xmin"] - pad_x)), max(0, int(b["ymin"] - pad_y)),
               min(width, int(b["xmax"] + pad_x)), min(height, int(b["ymax"] + pad_y)))
        buffer = io.BytesIO()
        image.crop(box).save(buffer, "JPEG", quality=90)
        pieces.append(Piece(category, name, round(item["score"], 3), box, buffer.getvalue()))
    return pieces


def person_crop(image_bytes: bytes, pieces: list[Piece]) -> bytes | None:
    """Ausschnitt um alle gefundenen Teile zusammen (die Person ohne viel Hintergrund) –
    darauf erkennt FashionCLIP Stil und Damen/Herren besser als auf dem ganzen Foto."""
    if not pieces:
        return None
    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    box = (min(p.box[0] for p in pieces), min(p.box[1] for p in pieces),
           max(p.box[2] for p in pieces), max(p.box[3] for p in pieces))
    buffer = io.BytesIO()
    image.crop(box).save(buffer, "JPEG", quality=90)
    return buffer.getvalue()
