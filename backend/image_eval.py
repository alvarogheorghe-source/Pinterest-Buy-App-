"""Wie genau erkennt Mali Bilder? – Messung mit eigenen Testbildern.

So geht's:
1. Ordner "testbilder" im Projekt anlegen (wird NICHT hochgeladen, steht in .gitignore)
2. Darin Unterordner nach dem, was auf den Bildern zu sehen ist:

       testbilder/Jacken/        Fotos/Screenshots mit Jacke als Hauptteil
       testbilder/Hosen/  …      jede Kategorie aus der App (Oberteile, Schuhe, Deko, Leuchten …)
       testbilder/_kein/         Bilder OHNE Mode/Wohnen (Desktop, Essen, Landschaft …)

   Optional im Dateinamen eine Marke und/oder Schnitt & Details mit "__" (details.py), z.B.
       testbilder/Schuhe/foto1__Adidas Samba.jpg
       testbilder/Hosen/foto2__Jeans__Bootcut__Light Wash.jpg
3. Starten:   python -m backend.image_eval            (oder: python -m backend.image_eval ordner/)

Ausgabe: pro Bild erkannt vs. erwartet und am Ende die Trefferquoten. Ändere danach Schwellen
oder Beschreibungen in image_tags.py und miss erneut – so sieht man, ob es besser wird.
"""

import sys
from pathlib import Path

from backend import details, image_tags, vision
from backend.brands import BRANDS
from backend.config import BASE_DIR
from backend.matching import CATEGORY_SYNONYMS

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
NONE_FOLDER = "_kein"


def expected_for(path: Path) -> dict:
    """testbilder/Hosen/bild__Bootcut__Light Wash.jpg
    -> {"category": "Hosen", "brand": None, "details": ["Bootcut", "Light Wash"]}"""
    folder = path.parent.name
    tags = path.stem.split("__")[1:]
    unknown = [t for t in tags if t not in BRANDS and t not in details.BY_NAME]
    if unknown:
        print(f"Hinweis: unbekannt im Dateinamen {path.name}: {', '.join(unknown)}")
    return {"category": None if folder == NONE_FOLDER else folder,
            "brand": next((t for t in tags if t in BRANDS), None),
            "details": [t for t in tags if t in details.BY_NAME]}


def collect(folder: Path) -> list[Path]:
    folders = [f for f in sorted(folder.iterdir()) if f.is_dir()]
    unknown = [f.name for f in folders if f.name != NONE_FOLDER and f.name not in CATEGORY_SYNONYMS]
    if unknown:
        print(f"Hinweis: unbekannte Ordner werden übersprungen: {', '.join(unknown)}")
        print(f"         erlaubt: {NONE_FOLDER}, {', '.join(CATEGORY_SYNONYMS)}\n")
    return [path for f in folders if f.name not in unknown
            for path in sorted(f.iterdir()) if path.suffix.lower() in IMAGE_TYPES]


def evaluate(paths: list[Path], embedder, store) -> dict:
    labels = image_tags.label_vectors(embedder, store)
    vectors = embedder.embed_image_bytes([p.read_bytes() for p in paths])
    counts = {"gate_ok": 0, "category_ok": 0, "category_total": 0, "brand_ok": 0, "brand_total": 0,
              "detail_ok": 0, "detail_total": 0, "detail_extra": 0}
    rows = []
    for path, vector in zip(paths, vectors):
        expected = expected_for(path)
        if vector is None:
            rows.append((path, "Bild nicht lesbar", False))
            continue
        result = image_tags.tag(vector, labels)
        should_be_relevant = expected["category"] is not None
        gate_ok = result["relevant"] == should_be_relevant
        counts["gate_ok"] += gate_ok
        ok = gate_ok
        if should_be_relevant:
            counts["category_total"] += 1
            category_ok = expected["category"] in result["categories"]
            counts["category_ok"] += category_ok
            ok = ok and category_ok
        if expected["brand"]:
            counts["brand_total"] += 1
            brand_ok = expected["brand"] in result["brands"]
            counts["brand_ok"] += brand_ok
            ok = ok and brand_ok
        found_details = [name for category, name in result["details"]
                         if category == expected["category"]]
        if expected["details"]:
            hits = [d for d in expected["details"] if d in found_details]
            counts["detail_total"] += len(expected["details"])
            counts["detail_ok"] += len(hits)
            # Erkannt, aber nicht im Dateinamen: falsch (oder im Namen vergessen)
            counts["detail_extra"] += len([d for d in found_details if d not in expected["details"]])
            ok = ok and len(hits) == len(expected["details"])
        seen = (", ".join(result["categories"] + [n for _, n in result["details"]]
                          + result["brands"] + result["styles"])
                if result["relevant"] else f"keine Mode/Wohnen ({result['seen'] or 'unklar'})")
        rows.append((path, seen, ok))
    return {"rows": rows, "counts": counts, "total": len(paths)}


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f} % ({part}/{whole})" if whole else "–"


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "testbilder"
    if not folder.is_dir():
        print(__doc__)
        sys.exit(1)
    paths = collect(folder)
    if not paths:
        print("Keine Bilder gefunden – siehe Anleitung oben in backend/image_eval.py.")
        sys.exit(1)
    print(f"Lade Modell und schaue mir {len(paths)} Bilder an …\n")
    embedder = vision.get_embedder()
    store = vision.EmbeddingStore(embedder.name)
    result = evaluate(paths, embedder, store)
    store.save()
    for path, seen, ok in result["rows"]:
        print(f"{'✓' if ok else '✗'} {path.parent.name}/{path.name[:38]:<38} -> {seen}")
    c = result["counts"]
    print("\nTrefferquote")
    print(f"  Mode/Wohnen richtig erkannt (Vorprüfung): {percent(c['gate_ok'], result['total'])}")
    print(f"  Richtige Kategorie:                       {percent(c['category_ok'], c['category_total'])}")
    print(f"  Richtige Marke:                           {percent(c['brand_ok'], c['brand_total'])}")
    print(f"  Schnitt & Details gefunden:               {percent(c['detail_ok'], c['detail_total'])}")
    print(f"  Zusätzlich erkannte Details (evtl. falsch): {c['detail_extra']}")


if __name__ == "__main__":
    main()
