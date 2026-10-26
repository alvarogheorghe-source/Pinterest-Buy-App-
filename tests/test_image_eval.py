"""Genauigkeitsmessung mit eigenen Testbildern (backend/image_eval.py) – simuliertes Modell."""

from backend import image_eval, vision
from tests.test_image_tags import MODE, FakeTextEmbedder, axis

# Was das "Modell" in den Testbildern sieht (nach Dateiname)
SEES = {
    b"jacke": axis(MODE, ("category:Jacken", 1.0)),
    b"samba": axis(("gate:shoes", 1.0), ("category:Schuhe", 1.0), ("brand:Adidas Samba", 1.0)),
    b"hose-als-jacke": axis(MODE, ("category:Jacken", 1.0)),            # Fehler des Modells
    b"desktop": axis(("gate:desktop", 1.0)),
    b"bootcut": axis(MODE, ("category:Hosen", 1.0), ("detail:Hosen|Bootcut", 1.0),
                     ("detail:Hosen|Leo", 1.0)),
}


class BytesEmbedder(FakeTextEmbedder):
    def embed_image_bytes(self, images):
        return [SEES[data] for data in images]


def test_measures_gate_category_and_brand(tmp_path):
    for folder, name, content in [("Jacken", "a.jpg", b"jacke"), ("Schuhe", "b__Adidas Samba.jpg", b"samba"),
                                  ("Hosen", "c.png", b"hose-als-jacke"), ("_kein", "d.png", b"desktop"),
                                  ("Unsinn", "e.jpg", b"jacke")]:
        (tmp_path / folder).mkdir(exist_ok=True)
        (tmp_path / folder / name).write_bytes(content)
    paths = image_eval.collect(tmp_path)
    assert len(paths) == 4                                        # Ordner "Unsinn" übersprungen
    result = image_eval.evaluate(paths, BytesEmbedder(), vision.EmbeddingStore("fake"))
    assert result["counts"] == {"gate_ok": 4, "category_ok": 2, "category_total": 3,
                                "brand_ok": 1, "brand_total": 1,
                                "detail_ok": 0, "detail_total": 0, "detail_extra": 0}
    wrong = [path.name for path, _, ok in result["rows"] if not ok]
    assert wrong == ["c.png"]


def test_measures_details_from_file_names(tmp_path):
    (tmp_path / "Hosen").mkdir()
    (tmp_path / "Hosen" / "f__Bootcut__Light Wash.jpg").write_bytes(b"bootcut")
    paths = image_eval.collect(tmp_path)
    assert image_eval.expected_for(paths[0])["details"] == ["Bootcut", "Light Wash"]
    counts = image_eval.evaluate(paths, BytesEmbedder(), vision.EmbeddingStore("fake"))["counts"]
    assert (counts["detail_ok"], counts["detail_total"], counts["detail_extra"]) == (1, 2, 1)
