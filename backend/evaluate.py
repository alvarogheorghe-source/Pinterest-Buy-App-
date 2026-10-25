"""Misst, wie gut die Vorschläge zu einzelnen Pins passen.

Ein Testset ist eine Liste von Pins, bei denen ein Mensch festgehalten hat,
welche Produkte wirklich passen ("relevant"). Für jeden Pin macht ein
"Empfehler" seine Vorschläge, und wir zählen:

- Treffer@1: Ist der ERSTE Vorschlag passend?
- Treffer@5: Ist unter den ersten 5 mindestens ein passender?
- Ø Platz:  Auf welchem Platz steht im Schnitt der erste passende Vorschlag?

Der Empfehler ist austauschbar – so können wir z.B. "Text" gegen "Bilder
(FashionCLIP)" vergleichen, mit genau demselben Testset.

Starten mit:  python -m backend.evaluate              (Demo-Testset)
              python -m backend.evaluate pfad.json    (eigenes Testset)
"""

import json
import sys
from pathlib import Path
from typing import Callable

from backend import matching, vision
from backend.config import BASE_DIR
from backend.products import Product, filter_products, get_product_source

DEMO_TESTSET = BASE_DIR / "eval" / "demo_testset.json"

# Ein Empfehler bekommt einen Pin, die Welt und alle Produkte und gibt
# Produkt-IDs zurück, beste zuerst. Leere Liste = "kein Signal gefunden".
Recommender = Callable[[dict, str, list[Product]], list[str]]


def text_recommender(pin: dict, department: str, products: list[Product]) -> list[str]:
    """Der heutige Weg (matching.py): Wörter aus Titel, Beschreibung, Alt-Text und
    Board-Name + die Hauptfarbe des Bildes."""
    profile = matching.build_style_profile([pin])
    ranked = matching.rank_products(filter_products(products, department=department), profile)
    # Produkte ohne einen einzigen gemeinsamen Begriff sind geraten, nicht erkannt
    return [r["id"] for r in ranked if r["score"] > 0]


def pin_text_only_recommender(pin: dict, department: str, products: list[Product]) -> list[str]:
    """Zum Vergleich: NUR Titel und Beschreibung (ohne Board-Name, Alt-Text, Bildfarbe)."""
    pin = {"title": pin.get("title"), "description": pin.get("description")}
    return text_recommender(pin, department, products)


# Alle Empfehler, die verglichen werden (Name -> Funktion). Später z.B. "Bilder (FashionCLIP)".
RECOMMENDERS = {
    "Nur Pin-Text": pin_text_only_recommender,
    "Text + Board + Bildfarbe": text_recommender,
}


def make_visual_recommenders(store: "vision.EmbeddingStore",
                             embedder: "vision.Embedder | None") -> dict[str, Recommender]:
    """Empfehler mit Bildern. Braucht pin["image_url"] im Testset und berechnete
    Produkt-Vektoren (python -m backend.vision). Pin-Bilder des Testsets werden bei
    Bedarf mit `embedder` berechnet und im Speicher gemerkt."""
    product_vectors = store.vectors("product:")

    def pin_vector(pin: dict) -> list[float] | None:
        url = pin.get("image_url")
        if not url:
            return None
        key = f"testpin:{url}"
        if store.get(key, url) is None and embedder is not None:
            vision.index(store, embedder, [(key, url)])
        return store.get(key, url)

    def visual(pin: dict, department: str, products: list[Product]) -> list[str]:
        """Nur Bilder: Produkte, deren Bild dem Pin-Bild am ähnlichsten ist."""
        vector = pin_vector(pin)
        if vector is None:
            return []
        scored = [(vision.cosine(vector, product_vectors[p.id]), p.price, p.id)
                  for p in filter_products(products, department=department)
                  if p.id in product_vectors]
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [pid for _, _, pid in scored]

    def hybrid(pin: dict, department: str, products: list[Product]) -> list[str]:
        """Text-Punkte (wie im Shop) + Bild-Punkte."""
        vector = pin_vector(pin)
        profile = matching.build_style_profile([pin])
        ranked = matching.rank_products(filter_products(products, department=department), profile)
        scored = []
        for r in ranked:
            looks = 0.0
            if vector is not None and r["id"] in product_vectors:
                looks = vision.visual_score(vision.cosine(vector, product_vectors[r["id"]]))
            scored.append((r["score"] + vision.VISUAL_WEIGHT * looks, r["price"], r["id"]))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [pid for score, _, pid in scored if score > 0]

    return {"Bilder": visual, "Text + Bilder": hybrid}


def load_testset(path: Path = DEMO_TESTSET) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["cases"]


def evaluate(cases: list[dict], recommender: Recommender, products: list[Product],
             k: int = 5) -> dict:
    """Wendet den Empfehler auf jeden Fall an und berechnet die Kennzahlen."""
    results = []
    for case in cases:
        ranking = recommender(case["pin"], case["department"], products)
        relevant = set(case["relevant"])
        # Platz des ersten passenden Vorschlags (1 = ganz oben), None = nicht gefunden
        first_hit = next((i + 1 for i, pid in enumerate(ranking) if pid in relevant), None)
        results.append({
            "id": case["id"],
            "top": ranking[:k],
            "first_hit": first_hit,
            "no_signal": len(ranking) == 0,
        })

    n = len(results) or 1
    found = [r["first_hit"] for r in results if r["first_hit"] is not None]
    return {
        "cases": results,
        "hit_at_1": sum(1 for r in results if r["first_hit"] == 1) / n,
        "hit_at_k": sum(1 for r in results if r["first_hit"] and r["first_hit"] <= k) / n,
        "k": k,
        "avg_rank": sum(found) / len(found) if found else None,
        "no_signal": sum(1 for r in results if r["no_signal"]),
        "total": len(results),
    }


def print_report(report: dict, products: list[Product], name: str = "Text") -> None:
    """Gibt das Ergebnis als übersichtliche Tabelle im Terminal aus."""
    names = {p.id: p.name for p in products}
    k = report["k"]
    print(f"\nEmpfehler: {name}\n")
    for r in report["cases"]:
        if r["no_signal"]:
            status = "–  kein Signal (kein bekanntes Wort im Pin)"
        elif r["first_hit"] and r["first_hit"] <= k:
            status = f"✓  Treffer auf Platz {r['first_hit']}"
        else:
            status = "✗  kein passender in den Top 5"
        top = ", ".join(names[pid] for pid in r["top"][:3]) or "–"
        print(f"  {r['id']:<14} {status}")
        print(f"  {'':<14}    Top 3: {top}")

    avg = f"{report['avg_rank']:.1f}" if report["avg_rank"] else "–"
    print(f"\n  Treffer@1:  {report['hit_at_1']:.0%}")
    print(f"  Treffer@{k}:  {report['hit_at_k']:.0%}")
    print(f"  Ø Platz des ersten Treffers (wenn gefunden): {avg}")
    print(f"  Kein Signal: {report['no_signal']} von {report['total']} Pins\n")


def print_comparison(reports: dict[str, dict]) -> None:
    """Kurze Tabelle: alle Empfehler nebeneinander."""
    print("Vergleich")
    print(f"  {'Empfehler':<28} {'Treffer@1':>9} {'Treffer@5':>9} {'kein Signal':>12}")
    for name, report in reports.items():
        print(f"  {name:<28} {report['hit_at_1']:>9.0%} {report['hit_at_k']:>9.0%} "
              f"{report['no_signal']:>8} / {report['total']}")
    print()


def main() -> None:
    """python -m backend.evaluate [--bilder] [testset.json]"""
    args = [a for a in sys.argv[1:] if a != "--bilder"]
    path = Path(args[0]) if args else DEMO_TESTSET
    products = get_product_source().load()
    cases = load_testset(path)
    recommenders = dict(RECOMMENDERS)

    if "--bilder" in sys.argv:
        store = vision.EmbeddingStore.load_existing()
        if store is None:
            print("Keine Bild-Vektoren gefunden. Zuerst: python -m backend.vision")
            sys.exit(1)
        try:
            embedder = vision.ClipEmbedder(store.model)  # für die Pin-Bilder des Testsets
        except vision.VisionUnavailable as err:
            print(f"Hinweis: {err} – nur bereits berechnete Pin-Bilder werden genutzt.")
            embedder = None
        recommenders.update(make_visual_recommenders(store, embedder))
        if not any(case["pin"].get("image_url") for case in cases):
            print("Hinweis: Das Testset enthält keine Bild-URLs (pin.image_url) – "
                  "für Bilder braucht es ein Testset mit echten Pins.")

    reports = {name: evaluate(cases, rec, products) for name, rec in recommenders.items()}
    if "--bilder" in sys.argv:
        store.save()  # neu berechnete Testset-Bilder merken
    # Ausführlich nur für den besten (letzten) Empfehler, dann der Vergleich
    last = list(reports)[-1]
    print_report(reports[last], products, name=last)
    print_comparison(reports)


if __name__ == "__main__":
    main()
