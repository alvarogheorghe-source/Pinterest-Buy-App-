"""Shop the Look (backend/looks.py): zu Outfit-Pins die passenden Teile."""

from backend import looks, storage
from tests.test_products import make_product


def pin(pin_id, title, **extra):
    return {"id": pin_id, "title": title, "image_url": f"https://i.pinimg.com/{pin_id}.jpg", **extra}


def test_outfit_parts_from_text_and_image():
    assert looks.outfit_parts(pin("1", "black bomber jacket, baggy jeans")) == ["Hosen", "Jacken"]
    assert looks.outfit_parts(pin("2", "outfit", image_categories=["Schuhe", "Oberteile"])) == \
        ["Oberteile", "Schuhe"]
    assert looks.outfit_parts(pin("3", "ceramic vase")) == []            # Wohnen zählt nicht


def test_best_item_per_part_and_no_duplicates():
    catalog = [
        make_product(id="jacke-schwarz", name="Bomberjacke", category="Jacken", colors=["schwarz"]),
        make_product(id="jacke-beige", name="Trenchcoat", category="Jacken", colors=["beige"]),
        make_product(id="jeans-baggy", name="Baggy Jeans", category="Hosen", colors=["blau"]),
        make_product(id="vase", name="Vase", category="Deko", department="wohnen"),
    ]
    pins = [pin("a", "black bomber jacket and baggy jeans"),
            pin("b", "black jacket with baggy jeans"),            # zweiter Look, gleiche Teile
            pin("c", "just a black jacket")]                      # nur ein Teil -> kein Look
    found = looks.shop_the_look(pins, catalog)
    assert [look["pin"]["id"] for look in found] == ["a"]
    assert {item["id"] for item in found[0]["items"]} == {"jacke-schwarz", "jeans-baggy"}


def test_api_looks(fake, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        pin("a", "beige oversized hoodie with black cargo pants and chunky sneakers")]})
    found = client.get("/api/looks").json()
    assert found and found[0]["pin"]["id"] == "a"
    assert {item["category"] for item in found[0]["items"]} >= {"Oberteile", "Hosen"}
    assert all("local_price" in item for item in found[0]["items"])
