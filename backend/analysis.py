"""Malis Hintergrund-Analyse: Nach "Pins laden" schaut sich Mali die Pins automatisch an.

Kein Terminal mehr nötig – die App startet alles selbst, im Hintergrund:

    1. farben        Hauptfarbe aus Pin-Bildern, wo Pinterest keine liefert (pin_colors.py)
    2. vorbereiten   KI-Modell laden (nur beim ersten Mal, dauert etwas)
    3. bilder        Pin- und Produktbilder in Vektoren umrechnen (vision.py)
    4. stil          Stil, Teile, Herren/Damen und Marken erkennen (image_tags.py)
    5. schwerpunkte  Stil-Schwerpunkte für schnelle Vergleiche (vision.build_clusters)

Die Website fragt GET /api/analysis ab und zeigt Mali, der dabei mit dir redet
(frontend/analysis.js). Ohne KI-Pakete laufen nur die Farben – die App funktioniert trotzdem.
"""

import contextvars
import hashlib
import threading
import time
from collections import Counter

from backend import pin_colors, storage

STATE_FILE = "analysis.json"
# Erhöhen, wenn sich die Erkennung ändert -> gespeicherte Pins werden automatisch neu angeschaut
VERSION = 2
STEPS = ["farben", "vorbereiten", "bilder", "stil", "schwerpunkte"]

_lock = threading.Lock()
_states: dict[str, dict] = {}   # Person -> Analyse-Stand (jede Person hat ihre eigene Analyse)


def pins_fingerprint(data: dict) -> str:
    """Ändert sich, sobald andere Pins geladen wurden -> dann ist eine neue Analyse nötig."""
    ids = ",".join(sorted(pin["id"] for pin in data.get("pins", [])))
    return hashlib.sha1(f"v{VERSION}|{data.get('fetched_at')}|{ids}".encode()).hexdigest()[:16]


def _load_state() -> dict:
    """Stand der aktuellen Person (aus dem Speicher, beim ersten Mal aus der Datenbank)."""
    user = storage.current_user()
    if user not in _states:
        saved = storage.read_json(STATE_FILE, default=None) or {}
        # Lief beim Beenden der App noch eine Analyse? Dann gilt sie als abgebrochen.
        if saved.get("status") == "running":
            saved.update(status="idle")
        _states[user] = saved or {"status": "idle"}
    return _states[user]


def _update(**changes) -> None:
    with _lock:
        state = _load_state()
        state.update(changes)
        storage.write_json(STATE_FILE, dict(state))


def forget_user() -> None:
    """Nach "Alle meine Daten löschen": auch den Stand im Speicher vergessen."""
    with _lock:
        _states.pop(storage.current_user(), None)


def status() -> dict:
    """Aktueller Stand – plus "needed": Gibt es Pins, die noch nicht angeschaut wurden?"""
    with _lock:
        state = dict(_load_state())
    data = storage.load_pins()
    state["needed"] = bool(data["pins"]) and state.get("status") != "running" \
        and state.get("pins") != pins_fingerprint(data)
    state["pin_count"] = len(data["pins"])
    return state


def _spawn(target) -> None:
    """Eigene Funktion, damit Tests die Analyse ohne Thread (sofort) laufen lassen können.
    copy_context: der Hintergrund-Thread arbeitet für dieselbe Person wie die Anfrage."""
    threading.Thread(target=contextvars.copy_context().run, args=(target,), daemon=True).start()


def start() -> dict:
    """Startet die Analyse im Hintergrund – außer sie läuft schon."""
    with _lock:
        state = _load_state()
        if state.get("status") == "running":
            return dict(state)
        state.update(status="running", step="farben", done=0, total=0, found=[],
                     error=None, vision=None, started_at=time.time(), finished_at=None)
    _spawn(run)
    return status()


def _summary(pins: list[dict]) -> list[str]:
    """Was Mali am häufigsten gesehen hat – für "Ich hab … entdeckt!" (max. 6 Begriffe)."""
    counts = Counter()
    for pin in pins:
        counts.update(pin.get("image_styles", []))
        counts.update(pin.get("image_categories", []))
        counts.update(pin.get("image_brands", []))
    return [term for term, _ in counts.most_common(6)]


def run() -> None:
    """Die eigentliche Arbeit. Läuft im Hintergrund-Thread; Fehler landen im Status."""
    from backend import image_tags, vision
    from backend.products import get_product_source
    try:
        data = storage.load_pins()
        _update(step="farben", done=0, total=len(data["pins"]))
        pin_colors.fill_missing_colors(data["pins"])
        storage.save_pins(data)

        _update(step="vorbereiten", done=0, total=0)
        try:
            embedder = vision.get_embedder()
        except vision.VisionUnavailable:
            # Ohne KI-Pakete: Farben + Text reichen für ein Grundprofil
            _update(status="done", step="fertig", vision=False, finished_at=time.time(),
                    pins=pins_fingerprint(storage.load_pins()))
            return

        store = vision.EmbeddingStore(embedder.name)
        pin_entries = [(f"pin:{pin['id']}", pin.get("image_url")) for pin in data["pins"]]
        product_entries = [(f"product:{p.id}", p.image_url) for p in get_product_source().load()]
        entries = pin_entries + product_entries
        _update(step="bilder", done=0, total=len(vision.missing(store, entries)))
        vision.index(store, embedder, entries,
                     on_progress=lambda done, total: _update(done=done, total=total))
        store.save()

        _update(step="stil", done=0, total=len(data["pins"]))
        image_tags.tag_pins(embedder, store)
        tagged = storage.load_pins()
        _update(found=_summary(tagged["pins"]))

        _update(step="schwerpunkte", done=0, total=0)
        vision.build_clusters(store, tagged["pins"])
        store.save()

        _update(status="done", step="fertig", vision=True, finished_at=time.time(),
                pins=pins_fingerprint(tagged))
    except Exception as err:  # nie die App abstürzen lassen – Mali meldet es freundlich
        _update(status="error", error=str(err)[:300], finished_at=time.time())
