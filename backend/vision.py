"""Bilderkennung (Phase 2): Bilder vergleichen statt nur Wörter.

Idee: Ein KI-Modell (FashionCLIP) wandelt jedes Bild in einen "Fingerabdruck"
um – eine Liste von 512 Zahlen (ein Vektor). Ähnlich aussehende Kleidung bekommt
ähnliche Vektoren. Wie ähnlich zwei Bilder sind, misst die Kosinus-Ähnlichkeit:
1.0 = gleich, um 0 = nichts gemeinsam.

Ablauf:
1. EINMAL (bzw. nach "Pins laden" / neuem Produkt-Feed) alle Bilder berechnen:
       python -m backend.vision
   -> speichert die Vektoren in data/embeddings.json
2. Die App vergleicht danach nur noch die gespeicherten Zahlen – das KI-Modell
   muss dafür NICHT laufen (schnell, kein Strom fressen).

Die KI-Pakete sind optional:  pip install -r requirements-ai.txt
Ohne sie (oder ohne data/embeddings.json) funktioniert die App wie bisher.
"""

import hashlib
import io
import threading
import math
import operator
import os
import sys
from typing import Protocol

import httpx

from backend import storage

# Modell austauschbar per .env: FashionCLIP ist auf Mode spezialisiert. Für Wohnen &
# Deko könnte "openai/clip-vit-base-patch32" besser sein – das zeigt die Messung.
DEFAULT_MODEL = "patrickjohncyh/fashion-clip"
EMBEDDINGS_FILE = "embeddings.json"
BATCH_SIZE = 16

# Wie stark "sieht ähnlich aus" zählt (im Vergleich: ein Begriff in JEDEM Pin = 1 Punkt)
VISUAL_WEIGHT = 2.0
# Kosinus-Werte zwischen zwei Fotos liegen bei CLIP selten unter ~0.5. Wir rechnen
# deshalb 0.5..1.0 auf 0..1 um, sonst bekäme fast alles Punkte.
VISUAL_FLOOR = 0.5
# Viele Pins? Dann werden ähnliche Pins zu Stil-Schwerpunkten (Gruppen) zusammengefasst.
# Ein Produkt wird erst mit den Schwerpunkten verglichen und dann nur mit den Pins der
# CLUSTER_PROBE ähnlichsten Gruppen – statt mit allen Pins. Bei 500 Pins ca. 5× weniger
# Rechenarbeit, bei 3000 noch viel mehr. Kleine Boards brauchen das nicht.
CLUSTERS = 12             # mindestens so viele Gruppen …
PINS_PER_CLUSTER = 40     # … bei vielen Pins ca. eine Gruppe pro 40 Pins
MAX_CLUSTERS = 80
CLUSTER_PROBE = 2
CLUSTER_MIN_PINS = 60     # darunter wird jeder Pin direkt verglichen (schnell genug)

# Ab hier sagen wir "Sieht aus wie deine Pins"
VISUAL_HINT_THRESHOLD = 0.6


class VisionUnavailable(Exception):
    """Die KI-Pakete fehlen oder das Modell kann nicht geladen werden."""


def model_name() -> str:
    return os.getenv("CLIP_MODEL", "").strip() or DEFAULT_MODEL


# --- Rechnen mit Vektoren (ohne Zusatzpakete) ---------------------------------------------

def normalize(vector: list[float]) -> list[float]:
    """Auf Länge 1 bringen – dann ist die Kosinus-Ähnlichkeit einfach das Skalarprodukt."""
    length = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / length, 5) for x in vector]


def cosine(a: list[float], b: list[float]) -> float:
    """Kosinus-Ähnlichkeit zweier NORMALISIERTER Vektoren (map + mul: ca. doppelt so schnell)."""
    return sum(map(operator.mul, a, b))


def visual_score(similarity: float) -> float:
    """Kosinus 0.5..1.0 -> 0..1 (darunter 0)."""
    return max(0.0, (similarity - VISUAL_FLOOR) / (1 - VISUAL_FLOOR))


# --- Das KI-Modell ------------------------------------------------------------------------------

class Embedder(Protocol):
    """Alles, was Bild-URLs in Vektoren verwandeln kann (echtes Modell oder Test-Ersatz)."""
    name: str

    def embed_image_urls(self, urls: list[str]) -> list[list[float] | None]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_image_bytes(self, images: list[bytes]) -> list[list[float] | None]: ...


class ClipEmbedder:
    """Das echte Modell (CLIP/FashionCLIP über die Bibliothek "transformers")."""

    def __init__(self, name: str | None = None):
        self.name = name or model_name()
        try:
            import torch  # noqa: F401  (nur prüfen, ob vorhanden)
            from PIL import Image  # noqa: F401
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as err:
            raise VisionUnavailable(
                "KI-Pakete fehlen. Installieren mit: pip install -r requirements-ai.txt"
            ) from err
        try:
            # Beim ersten Mal lädt das ca. 600 MB von huggingface.co herunter
            self.model = CLIPModel.from_pretrained(self.name).eval()
            self.processor = CLIPProcessor.from_pretrained(self.name)
        except Exception as err:
            raise VisionUnavailable(f"Modell '{self.name}' konnte nicht geladen werden: {err}")

    @staticmethod
    def download(url: str):
        """Lädt ein Bild: eigene Bilder der App ("/img/...") direkt von der Festplatte,
        sonst per http(s), z.B. vom Pinterest-CDN."""
        from PIL import Image
        if url.startswith("/") and not url.startswith("//"):
            from backend.config import FRONTEND_DIR
            path = (FRONTEND_DIR / url.lstrip("/")).resolve()
            if FRONTEND_DIR.resolve() not in path.parents:  # nicht aus frontend/ ausbrechen
                raise ValueError("Pfad außerhalb von frontend/")
            return Image.open(path).convert("RGB")
        if not url.startswith(("https://", "http://")):
            raise ValueError("keine Web-Adresse")
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")

    def embed_image_urls(self, urls: list[str]) -> list[list[float] | None]:
        images: list = []
        for url in urls:
            try:
                images.append(self.download(url))
            except Exception:
                images.append(None)  # kaputtes/fehlendes Bild -> None
        return self._embed(images)

    def embed_image_bytes(self, images: list[bytes]) -> list[list[float] | None]:
        """Hochgeladene Fotos (Foto-Suche) – direkt aus dem Speicher, nichts wird gespeichert."""
        from PIL import Image
        opened: list = []
        for data in images:
            try:
                opened.append(Image.open(io.BytesIO(data)).convert("RGB"))
            except Exception:
                opened.append(None)
        return self._embed(opened)

    def _embed(self, opened: list) -> list[list[float] | None]:
        """Bilder (PIL, None = nicht ladbar) -> Vektoren."""
        import torch
        images = [image for image in opened if image is not None]
        positions = [i for i, image in enumerate(opened) if image is not None]
        results: list[list[float] | None] = [None] * len(opened)
        if images:
            with torch.no_grad():  # nur rechnen, nicht trainieren
                inputs = self.processor(images=images, return_tensors="pt")
                features = self.model.get_image_features(**inputs)
            # transformers 4.x liefert direkt die Zahlen (Tensor), 5.x ein Objekt,
            # in dem sie unter "pooler_output" stecken
            if not isinstance(features, torch.Tensor):
                features = features.pooler_output
            for position, feature in zip(positions, features):
                results[position] = normalize(feature.tolist())
        return results

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Sätze -> Vektoren im selben "Raum" wie die Bilder (für image_tags.py)."""
        import torch
        with torch.no_grad():
            inputs = self.processor(text=texts, return_tensors="pt", padding=True)
            features = self.model.get_text_features(**inputs)
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output
        return [normalize(feature.tolist()) for feature in features]


_embedder: dict = {}


def get_embedder() -> "ClipEmbedder":
    """Das Modell nur EINMAL laden und im Speicher behalten (Laden dauert, Rechnen geht dann
    schnell). Wirft VisionUnavailable, wenn die KI-Pakete fehlen."""
    if "model" not in _embedder:
        _embedder["model"] = ClipEmbedder()
    return _embedder["model"]


# --- Speicher für die Vektoren -----------------------------------------------------------------

_loaded: dict = {}   # zuletzt gelesene embeddings.json (siehe load_existing)
_save_lock = threading.Lock()
MAX_CLUSTER_SETS = 500  # Stil-Schwerpunkte von so vielen Pin-Auswahlen aufheben


class EmbeddingStore:
    """data/embeddings.json: {"model": "...", "items": {"product:prod-001": {"url", "vector"}}}

    Ändert sich die Bild-URL eines Eintrags, gilt sein Vektor als veraltet.
    Wird ein anderes Modell benutzt, beginnen wir von vorn (Vektoren verschiedener
    Modelle sind nicht vergleichbar).
    """

    def __init__(self, model: str, data: dict | None = None):
        if data is None:
            data = storage.read_json(EMBEDDINGS_FILE, default=None) or {}
        self.model = model
        same = data.get("model") == model
        self.items = data.get("items", {}) if same else {}
        # Stil-Schwerpunkte je Pin-Auswahl (Fingerabdruck) – jede Person hat ihre eigenen
        # {"<fingerabdruck>": [gruppen …]}
        self.clusters = data.get("clusters", {}) if same else {}
        if any(isinstance(v, dict) for v in self.clusters.values()):
            self.clusters = {}   # altes Format (je Welt) -> einfach neu berechnen

    @classmethod
    def load_existing(cls) -> "EmbeddingStore | None":
        """Den gespeicherten Stand laden, egal mit welchem Modell (für die App).

        Die Datei kann viele MB groß sein – sie wird nur neu gelesen, wenn sie sich
        geändert hat, sonst kommt der Stand aus dem Speicher.
        """
        path = storage.DATA_DIR / EMBEDDINGS_FILE
        try:
            stamp = (str(path), path.stat().st_mtime_ns)
        except FileNotFoundError:
            return None
        if _loaded.get("stamp") != stamp:
            data = storage.read_json(EMBEDDINGS_FILE, default=None)
            store = cls(data["model"], data) if data and data.get("items") else None
            _loaded.update(stamp=stamp, store=store)
        return _loaded["store"]

    def get(self, key: str, url: str | None = None) -> list[float] | None:
        entry = self.items.get(key)
        if not entry or (url is not None and entry["url"] != url):
            return None
        return entry["vector"]

    def put(self, key: str, url: str, vector: list[float]) -> None:
        self.items[key] = {"url": url, "vector": vector}

    def save(self) -> None:
        """Speichern – dabei Neues anderer Personen behalten (mehrere Analysen gleichzeitig)."""
        with _save_lock:
            current = storage.read_json(EMBEDDINGS_FILE, default=None) or {}
            if current.get("model") == self.model:
                self.items = {**current.get("items", {}), **self.items}
                self.clusters = {**current.get("clusters", {}), **self.clusters}
            # nur die neuesten Stil-Schwerpunkte behalten
            self.clusters = dict(list(self.clusters.items())[-MAX_CLUSTER_SETS:])
            storage.write_json(EMBEDDINGS_FILE, {"model": self.model, "items": self.items,
                                                 "clusters": self.clusters})

    def vectors(self, prefix: str) -> dict[str, list[float]]:
        """Alle Vektoren einer Sorte, z.B. prefix="product:" -> {"prod-001": [...]}"""
        return {key[len(prefix):]: entry["vector"]
                for key, entry in self.items.items() if key.startswith(prefix)}


def missing(store: EmbeddingStore, entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Welche Bilder müssen (neu) berechnet werden?"""
    return [(key, url) for key, url in entries if url and store.get(key, url) is None]


def index(store: EmbeddingStore, embedder: Embedder, entries: list[tuple[str, str]],
          on_progress=None) -> dict:
    """Berechnet fehlende/veraltete Vektoren. entries = [(schlüssel, bild_url), ...]
    on_progress(fertig, insgesamt) wird nach jedem Bild-Stapel aufgerufen (für Malis Anzeige)."""
    todo = missing(store, entries)
    failed = 0
    for start in range(0, len(todo), BATCH_SIZE):
        batch = todo[start:start + BATCH_SIZE]
        vectors = embedder.embed_image_urls([url for _, url in batch])
        for (key, url), vector in zip(batch, vectors):
            if vector is None:
                failed += 1
            else:
                store.put(key, url, vector)
        if on_progress:
            on_progress(start + len(batch), len(todo))
    return {"total": len(entries), "new": len(todo) - failed, "failed": failed}


def index_all(embedder: Embedder) -> dict:
    """Alle Produkte und gespeicherten Pins berechnen und speichern."""
    from backend.products import get_product_source
    store = EmbeddingStore(embedder.name)
    product_entries = [(f"product:{p.id}", p.image_url) for p in get_product_source().load()]
    pin_entries = [(f"pin:{pin['id']}", pin.get("image_url"))
                   for pin in storage.load_pins()["pins"]]
    result = {
        "products": index(store, embedder, product_entries),
        "pins": index(store, embedder, pin_entries),
    }
    store.save()
    return result


# --- Wie sehr ähnelt ein Produkt den Pins? ------------------------------------------------------

def pin_affinity(product_vector: list[float], pin_vectors: list[list[float]],
                 top: int = 3) -> float:
    """Wie sehr sieht ein Produkt aus wie die Pins? Durchschnitt der `top` ähnlichsten
    Pins, umgerechnet auf 0..1. (Nur die ähnlichsten zählen: Wer 200 Pins hat, mag
    nicht alles gleichzeitig – ein Produkt muss nur zu EINIGEN Pins passen.)"""
    if not pin_vectors:
        return 0.0
    best = sorted((cosine(product_vector, v) for v in pin_vectors), reverse=True)[:top]
    return visual_score(sum(best) / len(best))


def pins_fingerprint(pin_ids: list[str]) -> str:
    """Kurzer Fingerabdruck einer Pin-Auswahl – ändern sich die Pins, passen die Gruppen nicht mehr."""
    return hashlib.sha1(",".join(sorted(pin_ids)).encode()).hexdigest()[:16]


def mean_direction(vectors: list[list[float]]) -> list[float]:
    return normalize([sum(column) / len(vectors) for column in zip(*vectors)])


def kmeans(vectors: dict[str, list[float]], k: int = CLUSTERS, rounds: int = 8) -> list[dict]:
    """Fasst ähnliche Pins zu k Gruppen zusammen -> [{"center": [...], "pins": [ids]}].

    Start: der erste Pin, dann immer der Pin, der allen bisherigen Mittelpunkten am
    unähnlichsten ist (so sind die Startpunkte gut verteilt und das Ergebnis jedes Mal gleich).
    """
    ids = list(vectors)
    centers = [vectors[ids[0]]]
    nearest = [cosine(vectors[i], centers[0]) for i in ids]
    while len(centers) < min(k, len(ids)):
        far = min(range(len(ids)), key=lambda n: nearest[n])
        centers.append(vectors[ids[far]])
        nearest = [max(old, cosine(vectors[i], centers[-1])) for old, i in zip(nearest, ids)]

    assignment: list[int] = []
    for _ in range(rounds):
        new = [max(range(len(centers)), key=lambda c: cosine(vectors[i], centers[c])) for i in ids]
        if new == assignment:
            break
        assignment = new
        for c in range(len(centers)):
            members = [vectors[i] for i, a in zip(ids, assignment) if a == c]
            if members:
                centers[c] = mean_direction(members)
    return [{"center": centers[c], "pins": [i for i, a in zip(ids, assignment) if a == c]}
            for c in range(len(centers)) if c in assignment]


def build_clusters(store: EmbeddingStore, pins: list[dict]) -> None:
    """Stil-Schwerpunkte je Welt berechnen (beim Analysieren, nicht bei jedem Klick)."""
    from backend.matching import classify_pin
    from backend.products import DEPARTMENTS
    for department in DEPARTMENTS:
        vectors = {pin["id"]: store.get(f"pin:{pin['id']}") for pin in pins
                   if department in classify_pin(pin)}
        vectors = {pin_id: v for pin_id, v in vectors.items() if v}
        if len(vectors) >= CLUSTER_MIN_PINS:
            k = min(MAX_CLUSTERS, max(CLUSTERS, len(vectors) // PINS_PER_CLUSTER))
            store.clusters[pins_fingerprint(list(vectors))] = kmeans(vectors, k)


def clustered_affinity(product_vector: list[float], groups: list[dict],
                       pin_vectors: dict[str, list[float]]) -> float:
    """Wie pin_affinity, aber nur mit den Pins der ähnlichsten Gruppen."""
    best = sorted(groups, key=lambda g: -cosine(product_vector, g["center"]))[:CLUSTER_PROBE]
    candidates = [pin_vectors[i] for group in best for i in group["pins"] if i in pin_vectors]
    return pin_affinity(product_vector, candidates)


def apply_visual(ranked: list[dict], pins: list[dict], department: str,
                 store: "EmbeddingStore | None") -> list[dict]:
    """Ergänzt die Text-Punkte aus matching.rank_products() um "sieht aus wie deine Pins".

    Ohne gespeicherte Vektoren bleibt alles, wie es ist.
    """
    from backend.matching import classify_pin
    if store is None:
        return ranked
    pin_vectors = {pin["id"]: store.get(f"pin:{pin['id']}") for pin in pins
                   if department in classify_pin(pin)}
    pin_vectors = {pin_id: v for pin_id, v in pin_vectors.items() if v}
    product_vectors = store.vectors("product:")
    if not pin_vectors:
        return ranked

    # Passende Stil-Schwerpunkte vorhanden? (nur wenn sie zu genau diesen Pins gehören)
    groups = store.clusters.get(pins_fingerprint(list(pin_vectors)))

    results = []
    for item in ranked:
        vector = product_vectors.get(item["id"])
        if not vector:
            affinity = 0.0
        elif groups:
            affinity = clustered_affinity(vector, groups, pin_vectors)
        else:
            affinity = pin_affinity(vector, list(pin_vectors.values()))
        results.append({
            **item,
            "score": round(item["score"] + VISUAL_WEIGHT * affinity, 3),
            "looks_like_pins": affinity >= VISUAL_HINT_THRESHOLD,
        })
    results.sort(key=lambda r: (-r["score"], r["price"]))
    return results


def main() -> None:
    """python -m backend.vision  -> alle Bilder berechnen"""
    print(f"Lade Modell {model_name()} (beim ersten Mal ca. 600 MB Download) …")
    try:
        embedder = ClipEmbedder()
    except VisionUnavailable as err:
        print(f"Fehler: {err}")
        sys.exit(1)
    result = index_all(embedder)
    for kind, stats in result.items():
        print(f"{kind:>9}: {stats['total']} insgesamt, {stats['new']} neu berechnet, "
              f"{stats['failed']} Bilder nicht ladbar")
    print(f"Gespeichert in {storage.DATA_DIR / EMBEDDINGS_FILE}")
    # Was ist auf den Pin-Bildern? -> Stil + Kategorie als Begriffe am Pin
    from backend import image_tags
    store = EmbeddingStore(embedder.name)
    tagged = image_tags.tag_pins(embedder, store)
    print(f"Bild-Begriffe für {tagged} Pins erkannt – ansehen mit:  python -m backend.image_tags")
    # Viele Pins? -> Stil-Schwerpunkte, damit der Shop schnell bleibt
    build_clusters(store, storage.load_pins()["pins"])
    store.save()
    print("Stil-Schwerpunkte aktualisiert.")


if __name__ == "__main__":
    main()
