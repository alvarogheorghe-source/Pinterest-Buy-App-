"""Kleidungsstücke auf einem Foto finden (backend/garments.py) – mit simuliertem Modell."""

from io import BytesIO

from PIL import Image

from backend import garments


def outfit_photo():
    """200x400: oben schwarze Jacke, unten blaue Hose, außen grüne Wiese."""
    image = Image.new("RGB", (200, 400), "#5a6b2e")
    image.paste(Image.new("RGB", (120, 160), "#151515"), (40, 40))
    image.paste(Image.new("RGB", (100, 170), "#2a4d9b"), (50, 200))
    buffer = BytesIO()
    image.save(buffer, "JPEG")
    return buffer.getvalue()


def box(x0, y0, x1, y1):
    return {"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1}


class FakeDetector:
    def __init__(self, found):
        self.found = found

    def detect(self, image):
        return self.found


OUTFIT = [
    {"label": "jacket", "score": 0.93, "box": box(40, 40, 160, 200)},
    {"label": "LABEL_6", "score": 0.88, "box": box(50, 200, 150, 370)},     # pants
    {"label": "watch", "score": 0.81, "box": box(60, 100, 90, 130)},        # suchen wir nicht
    {"label": "sleeve", "score": 0.95, "box": box(40, 40, 70, 150)},        # kein Teil -> weg
    {"label": "shirt, blouse", "score": 0.3, "box": box(60, 60, 140, 120)},  # unsicher -> weg
]


def test_finds_the_pieces_biggest_first():
    pieces = garments.find(outfit_photo(), FakeDetector(OUTFIT))
    assert [(p.category, p.label) for p in pieces] == [("Jacken", "jacket"), ("Hosen", "pants")]
    jacket = Image.open(BytesIO(pieces[0].crop))
    assert jacket.getpixel((jacket.width // 2, jacket.height // 2))[0] < 40   # schwarz, keine Wiese


def test_one_piece_per_category_and_at_most_three():
    two_shoes = [{"label": "shoe", "score": 0.9, "box": box(0, 300, 90, 400)},
                 {"label": "shoe", "score": 0.9, "box": box(100, 300, 200, 400)}]
    many = OUTFIT[:2] + two_shoes + [{"label": "bag, wallet", "score": 0.9, "box": box(0, 0, 60, 60)},
                                     {"label": "hat", "score": 0.9, "box": box(0, 0, 50, 50)}]
    pieces = garments.find(outfit_photo(), FakeDetector(many))
    assert len(pieces) == garments.MAX_PIECES
    assert [p.category for p in pieces].count("Schuhe") <= 1


def test_without_model_nothing_changes():
    assert garments.find(outfit_photo()) == []            # conftest: kein Modell


def test_person_crop_leaves_out_the_background():
    pieces = garments.find(outfit_photo(), FakeDetector(OUTFIT))
    person = Image.open(BytesIO(garments.person_crop(outfit_photo(), pieces)))
    assert person.width < 200 and person.height < 400


def test_small_shoes_count_and_both_shoes_are_one_crop():
    shoes = [{"label": "shoe", "score": 0.9, "box": box(50, 372, 75, 392)},
             {"label": "shoe", "score": 0.85, "box": box(120, 372, 148, 392)}]
    pieces = garments.find(outfit_photo(), FakeDetector(OUTFIT + shoes))
    shoe = next(p for p in pieces if p.category == "Schuhe")
    assert shoe.box[0] < 50 and shoe.box[2] > 148                      # beide Schuhe drauf


def test_upper_body_searches_tops_and_jackets():
    """Zip-Hoodie heißt beim Modell "jacket", liegt bei uns aber unter Oberteile."""
    assert set(garments.search_categories("Jacken")) == {"Jacken", "Oberteile"}
    assert garments.search_categories("Hosen") == ["Hosen"]
