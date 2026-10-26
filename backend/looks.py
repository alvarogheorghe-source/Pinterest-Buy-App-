"""Shop the Look: zu einem Outfit-Pin die passenden Teile – Jacke, Hose, Schuhe …

Viele Pins zeigen ein ganzes Outfit. Malipin sucht Pins mit mindestens zwei Mode-Teilen
(aus Text oder Bilderkennung) und wählt pro Teil das Angebot, das am besten zu GENAU diesem
Pin passt (Farbe, Stil, Schnitt & Details, und – falls berechnet – wie ähnlich es aussieht).
"""

from backend import matching, vision
from backend.matching import CATEGORY_PATTERNS, CATEGORY_SYNONYMS, find_terms, pin_text
from backend.products import Product

MAX_LOOKS = 3
MIN_PARTS = 2          # ein "Look" hat mindestens zwei Teile
MAX_PARTS = 4


def outfit_parts(pin: dict) -> list[str]:
    """Mode-Kategorien eines Pins (Text + Bild), z.B. ["Jacken", "Hosen", "Schuhe"]."""
    found = find_terms(pin_text(pin), CATEGORY_PATTERNS) | set(pin.get("image_categories", []))
    return sorted(c for c in found if CATEGORY_SYNONYMS[c][0] == "mode")


def shop_the_look(pins: list[dict], products: list[Product], store=None,
                  limit: int = MAX_LOOKS) -> list[dict]:
    """[{"pin": {...}, "items": [Produkt je Teil]}, …] – die Pins mit den meisten Teilen zuerst."""
    outfits = [(pin, outfit_parts(pin)) for pin in pins
               if pin.get("image_url") and pin.get("image_relevant") is not False]
    outfits = [(pin, parts) for pin, parts in outfits if len(parts) >= MIN_PARTS]
    outfits.sort(key=lambda o: -len(o[1]))       # stabil: bei Gleichstand die neueren Pins zuerst

    looks, used = [], set()
    for pin, parts in outfits:
        profile = matching.build_style_profile([pin], "mode")
        items = []
        for part in parts[:MAX_PARTS]:
            candidates = [p for p in products if p.category == part and p.id not in used]
            ranked = vision.apply_visual(matching.rank_products(candidates, profile), [pin],
                                         "mode", store)
            best = next((r for r in ranked if r["score"] > 0), None)
            if best:
                items.append(best)
                used.add(best["id"])                 # dasselbe Teil nicht in zwei Looks
        if len(items) >= MIN_PARTS:
            looks.append({"pin": {"id": pin["id"], "title": pin.get("title") or "",
                                  "image_url": pin["image_url"]},
                          "items": items})
        if len(looks) >= limit:
            break
    return looks
