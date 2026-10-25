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

import io
import math
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
    """Kosinus-Ähnlichkeit zweier NORMALISIERTER Vektoren."""
    return sum(x * y for x, y in zip(a, b))


def visual_score(similarity: float) -> float:
    """Kosinus 0.5..1.0 -> 0..1 (darunter 0)."""
    return max(0.0, (similarity - VISUAL_FLOOR) / (1 - VISUAL_FLOOR))


# --- Das KI-Modell ------------------------------------------------------------------------------

class Embedder(Protocol):
    """Alles, was Bild-URLs in Vektoren verwandeln kann (echtes Modell oder Test-Ersatz)."""
    name: str

    def embed_image_urls(self, urls: list[str]) -> list[list[float] | None]: ...


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
        import torch
        images, positions = [], []
        for i, url in enumerate(urls):
            try:
                images.append(self.download(url))
                positions.append(i)
            except Exception:
                pass  # kaputtes/fehlendes Bild -> None
        results: list[list[float] | None] = [None] * len(urls)
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


# --- Speicher für die Vektoren -----------------------------------------------------------------

class EmbeddingStore:
    """data/embeddings.json: {"model": "...", "items": {"product:prod-001": {"url", "vector"}}}

    Ändert sich die Bild-URL eines Eintrags, gilt sein Vektor als veraltet.
    Wird ein anderes Modell benutzt, beginnen wir von vorn (Vektoren verschiedener
    Modelle sind nicht vergleichbar).
    """

    def __init__(self, model: str):
        data = storage.read_json(EMBEDDINGS_FILE, default=None) or {}
        self.model = model
        self.items = data.get("items", {}) if data.get("model") == model else {}

    @classmethod
    def load_existing(cls) -> "EmbeddingStore | None":
        """Den gespeicherten Stand laden, egal mit welchem Modell (für die App)."""
        data = storage.read_json(EMBEDDINGS_FILE, default=None)
        if not data or not data.get("items"):
            return None
        return cls(data["model"])

    def get(self, key: str, url: str | None = None) -> list[float] | None:
        entry = self.items.get(key)
        if not entry or (url is not None and entry["url"] != url):
            return None
        return entry["vector"]

    def put(self, key: str, url: str, vector: list[float]) -> None:
        self.items[key] = {"url": url, "vector": vector}

    def save(self) -> None:
        storage.write_json(EMBEDDINGS_FILE, {"model": self.model, "items": self.items})

    def vectors(self, prefix: str) -> dict[str, list[float]]:
        """Alle Vektoren einer Sorte, z.B. prefix="product:" -> {"prod-001": [...]}"""
        return {key[len(prefix):]: entry["vector"]
                for key, entry in self.items.items() if key.startswith(prefix)}


def index(store: EmbeddingStore, embedder: Embedder, entries: list[tuple[str, str]]) -> dict:
    """Berechnet fehlende/veraltete Vektoren. entries = [(schlüssel, bild_url), ...]"""
    todo = [(key, url) for key, url in entries if url and store.get(key, url) is None]
    failed = 0
    for start in range(0, len(todo), BATCH_SIZE):
        batch = todo[start:start + BATCH_SIZE]
        vectors = embedder.embed_image_urls([url for _, url in batch])
        for (key, url), vector in zip(batch, vectors):
            if vector is None:
                failed += 1
            else:
                store.put(key, url, vector)
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


def apply_visual(ranked: list[dict], pins: list[dict], department: str,
                 store: "EmbeddingStore | None") -> list[dict]:
    """Ergänzt die Text-Punkte aus matching.rank_products() um "sieht aus wie deine Pins".

    Ohne gespeicherte Vektoren bleibt alles, wie es ist.
    """
    from backend.matching import classify_pin
    if store is None:
        return ranked
    pin_vectors = [store.get(f"pin:{pin['id']}") for pin in pins
                   if department in classify_pin(pin)]
    pin_vectors = [v for v in pin_vectors if v]
    product_vectors = store.vectors("product:")
    if not pin_vectors:
        return ranked

    results = []
    for item in ranked:
        vector = product_vectors.get(item["id"])
        affinity = pin_affinity(vector, pin_vectors) if vector else 0.0
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


if __name__ == "__main__":
    main()
