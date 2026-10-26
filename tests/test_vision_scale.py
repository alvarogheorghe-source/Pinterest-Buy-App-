"""Viele Pins: Stil-Schwerpunkte (vision.kmeans/build_clusters) und Zwischenspeicher."""

import random

from backend import storage, vision


def noisy(base, rng, noise=0.15):
    return vision.normalize([x + rng.gauss(0, noise) for x in base])


def board(rng, groups=4, per_group=40, dims=32):
    """Pins in 4 klaren Stil-Gruppen (z.B. Jeans-Outfits, Sneaker, Lampen, Vasen)."""
    bases = [vision.normalize([rng.gauss(0, 1) for _ in range(dims)]) for _ in range(groups)]
    vectors = {f"{g}-{n}": noisy(bases[g], rng) for g in range(groups) for n in range(per_group)}
    return bases, vectors


def test_kmeans_finds_the_style_groups():
    rng = random.Random(1)
    _, vectors = board(rng)
    groups = vision.kmeans(vectors, k=4)
    assert len(groups) == 4
    for group in groups:                       # jede Gruppe enthält nur Pins EINER Stil-Gruppe
        assert len({pin_id.split("-")[0] for pin_id in group["pins"]}) == 1


def test_fast_way_gives_the_same_result_as_comparing_every_pin():
    rng = random.Random(2)
    bases, vectors = board(rng)
    groups = vision.kmeans(vectors, k=8)
    for base in bases + [vision.normalize([rng.gauss(0, 1) for _ in range(32)])]:
        product = noisy(base, rng, 0.1)
        exact = vision.pin_affinity(product, list(vectors.values()))
        fast = vision.clustered_affinity(product, groups, vectors)
        assert abs(exact - fast) < 0.01


def store_with_pins(rng, n):
    store = vision.EmbeddingStore("fake-model")
    _, vectors = board(rng, per_group=n // 4)
    pins = [{"id": pin_id, "title": "outfit"} for pin_id in vectors]
    for pin_id, vector in vectors.items():
        store.put(f"pin:{pin_id}", "x", vector)
    store.put("product:p1", "x", next(iter(vectors.values())))
    return store, pins


def test_clusters_are_used_only_for_the_same_pins(fake):
    store, pins = store_with_pins(random.Random(3), 120)
    vision.build_clusters(store, pins)
    assert len(store.clusters) == 1                             # "outfit" = nur Mode
    ranked = [{"id": "p1", "score": 0.0, "price": 10}]
    with_groups = vision.apply_visual(ranked, pins, "mode", store)[0]["score"]
    # Neue Pins geladen (einer fehlt) -> Gruppen passen nicht mehr -> genauer Vergleich
    without_groups = vision.apply_visual(ranked, pins[:-1], "mode", store)[0]["score"]
    assert with_groups > 1.0 and abs(with_groups - without_groups) < 0.05


def test_small_boards_need_no_clusters(fake):
    store, pins = store_with_pins(random.Random(4), 20)
    vision.build_clusters(store, pins)
    assert store.clusters == {}


def test_embeddings_file_is_read_only_when_it_changed(fake, monkeypatch):
    store, _ = store_with_pins(random.Random(5), 8)
    store.save()
    reads = []
    original = storage.read_json
    monkeypatch.setattr(storage, "read_json", lambda *a, **k: reads.append(a) or original(*a, **k))
    first = vision.EmbeddingStore.load_existing()
    assert vision.EmbeddingStore.load_existing() is first and len(reads) == 1
    store.put("product:p2", "x", [1.0])
    store.save()
    reads.clear()                                              # (Speichern liest selbst einmal)
    assert vision.EmbeddingStore.load_existing() is not first and len(reads) == 1
