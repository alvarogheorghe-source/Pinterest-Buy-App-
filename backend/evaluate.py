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

from backend import matching
from backend.config import BASE_DIR
from backend.products import Product, filter_products, get_product_source

DEMO_TESTSET = BASE_DIR / "eval" / "demo_testset.json"

# Ein Empfehler bekommt einen Pin, die Welt und alle Produkte und gibt
# Produkt-IDs zurück, beste zuerst. Leere Liste = "kein Signal gefunden".
Recommender = Callable[[dict, str, list[Product]], list[str]]


def text_recommender(pin: dict, department: str, products: list[Product]) -> list[str]:
    """Der heutige Weg: Wörter aus Titel und Beschreibung (matching.py)."""
    profile = matching.build_style_profile([pin])
    ranked = matching.rank_products(filter_products(products, department=department), profile)
    # Produkte ohne einen einzigen gemeinsamen Begriff sind geraten, nicht erkannt
    return [r["id"] for r in ranked if r["score"] > 0]


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


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO_TESTSET
    products = get_product_source().load()
    report = evaluate(load_testset(path), text_recommender, products)
    print_report(report, products)


if __name__ == "__main__":
    main()
