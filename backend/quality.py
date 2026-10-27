"""Was kommt ins Shop-Fenster? Gemeinsame Regeln für ALLE Quellen (Feeds, eBay, Etsy, AliExpress).

- Keine Unterwäsche, Socken, Bademode, Dessous, Kostüme, Kinderkleidung
- Kein Ramsch: Autoteile/Technik, Großhandels-Titel, Stichwort-Listen, Billigware
- Nur Titel, die unsere Besucher lesen können (Deutsch/Englisch)
"""

import re
import time

from backend import currency

# Passt nicht ins Shop-Fenster: Unterwäsche, Socken, Bademode (keine eigene Kategorie – "Pants"
# ist auf Britisch eine Unterhose!) und Kinderkleidung. "Slip Dress" / "Slip-On" sind ok.
NOT_SHOWN = re.compile(
    r"\b(boxer\w*|briefs?|slips?(?![\s-]*(dress|kleid|on|rock|skirt))|panty|panties|thongs?|"
    r"tanga|string-?tanga|unterhose\w*|unterwäsche|underwear|lingerie|dessous|bhs?|bras?|"
    r"bralettes?|socken|socks?|strümpfe|strumpfhose\w*|tights|pyjamas?|schlafanzug\w*|"
    r"bademode|bikini\w*|badeanzug\w*|swimsuit\w*|swimwear|badehose\w*|bielizna|majtki|"
    r"skarpet\w*|jazz-pants|hipster|ondergoed|sokken|nightwear|sleepwear|nachtwäsche|teddy|"
    r"sexy|erotic\w*|cosplay|costumes?|kostüm\w*|kostium\w*)\b", re.I)
# Kein Mode/Wohnen, auch wenn ein Wort danach klingt: auf Englisch ist "hose" ein Schlauch,
# "cap" ein Deckel – große Marktplätze (AliExpress) haben auch Autoteile, Technik, Werkzeug
JUNK = re.compile(
    r"\b(automo\w*|autoteil\w*|car|cars|motor\w*|vehicles?|engines?|fuel|carbur\w*|gaskets?|"
    r"spare parts?|replacement|connectors?|adapters?|fittings?|valves?|bolts?|screws?|"
    r"bearings?|pumps?|hydraul\w*|pneumat\w*|scuba|diving|regulators?|fishing|hardware|"
    r"electronic\w*|computer\w*|smartphones?|phone|phones|charger\w*|toys?|spielzeug\w*|"
    r"samochod\w*|motoryzac\w*|narzędz\w*|elektroni\w*|telefon\w*|wędkar\w*|zabawk\w*|"
    r"briggs|yamaha|honda|bmw|audi|volkswagen|vw|toyota|ford)\b", re.I)
KIDS = re.compile(r"\b(kinder\w*|kids?|baby|babys|children'?s?|girls?|boys?|mädchen|jungen|"
                  r"junior|toddler|dziec\w*|niemowl\w*)\b", re.I)


# --- Qualität: Billigware und Ramsch kommen gar nicht erst in den Shop ---------------------------
# Mindestpreis pro Kategorie (in Euro umgerechnet) – darunter ist es fast immer Wegwerfware
MIN_PRICE_EUR = {
    "Oberteile": 8, "Hosen": 12, "Jacken": 20, "Kleider & Röcke": 12, "Schuhe": 20,
    "Accessoires": 6, "Deko": 5, "Leuchten": 12, "Textilien": 8, "Küche & Tisch": 5,
    "Möbel": 30, "Pflanzen & Töpfe": 5, "Wandgestaltung": 6,
}
# Typische Ramsch-Titel: Großhandel, Stückzahlen, "Hot Sale", Kopien
SPAM = re.compile(
    r"\b(hot sale|free shipping|dropship\w*|wholesale|\d+\s?pcs?|\d+\s?pieces|lot of|"
    r"new arrivals?|high quality|best sellers?|1:1|replicas?|aaa+|cheap|clearance|"
    r"myster(y|ious) box|random|20[12]\d\s+new|new\s+20[12]\d)\b", re.I)
MAX_TITLE = 110          # längere Titel sind Stichwort-Listen ("… Women Men Summer Casual …")
# Titel in Sprachen, die unsere Besucher (Deutsch/Englisch) nicht lesen: Polnisch, Niederländisch,
# Französisch, Italienisch, Spanisch – typische Buchstaben und kleine Wörter
FOREIGN = re.compile(
    r"[ąęłńśźżć]|\b(dla|oraz|damsk\w*|męsk\w*|meski\w*|rozmiar|kolor|voor|dames|heren|maat|"
    r"kleur|pour|femme|homme|avec|couleur|donna|uomo|taglia|colore|para|mujer|hombre|"
    r"talla)\b", re.I)


_rates_cache: dict = {"at": 0.0, "table": None}


def _rates() -> dict:
    """Wechselkurse für den Import – einmal pro Minute statt für jede der 150.000 Zeilen lesen."""
    if time.time() - _rates_cache["at"] > 60:
        _rates_cache.update(at=time.time(), table=currency.rates())
    return _rates_cache["table"]


def low_quality(name: str, price: float, currency_code: str, category: str) -> bool:
    """Billigware, Ramsch-Titel oder eine Sprache, die unsere Besucher nicht lesen."""
    if len(name) > MAX_TITLE or SPAM.search(name) or FOREIGN.search(name):
        return True
    euro = currency.convert(price, currency_code, "EUR", _rates())
    return euro is not None and euro < MIN_PRICE_EUR.get(category, 0)


def rejected(name: str, category_text: str, department: str, price: float, currency_code: str,
             category: str, min_price: bool = True) -> bool:
    """True = nicht zeigen. min_price=False für Second-Hand (gebraucht darf günstig sein)."""
    text = f"{category_text} {name}"
    if JUNK.search(text):
        return True
    if department == "mode" and (NOT_SHOWN.search(text) or KIDS.search(text)):
        return True
    if not min_price:
        return len(name) > MAX_TITLE or bool(SPAM.search(name) or FOREIGN.search(name))
    return low_quality(name, price, currency_code, category)
