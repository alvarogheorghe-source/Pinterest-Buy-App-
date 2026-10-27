"""Passende Kleidung: Damen/Herren, keine Unterwäsche/Kinderkleidung, Größen nur einmal."""

from backend import feeds, matching

FEED = {"name": "awin-1", "preset": "awin", "currencies": []}


def row(n, name, category="", gender=""):
    return {"aw_product_id": str(n), "product_name": name, "aw_deep_link": f"https://a.b/{n}",
            "merchant_image_url": f"https://img/{n}.jpg", "search_price": "30", "currency": "EUR",
            "merchant_name": "Thought", "merchant_category": category,
            "Fashion:suitable_for": gender}


def test_gender_from_column_category_or_name():
    assert matching.gender_of("female") == "damen"
    assert matching.gender_of("", "Herren > Hosen", "Chino") == "herren"
    assert matching.gender_of("unisex", "", "Women's Wide Leg Jeans") == "damen"
    assert matching.gender_of("Jeans", "Hosen") is None
    assert matching.gender_of("Boyfriend Jeans") is None                # "boy" ≠ Kinder/Herren


def test_pins_decide_only_when_clear():
    women = [{"title": "Damen Outfit Herbst"}, {"title": "women street style"}, {"title": "Jeans"}]
    assert matching.pins_gender(women) == "damen"
    assert matching.pins_gender([{"title": "Jeans"}]) is None
    assert matching.pins_gender([{"title": "men outfit"}, {"title": "damen look"}]) is None


def test_underwear_and_kids_are_not_shown_but_slip_dress_is():
    assert feeds.to_product(row(1, "Pants Modell: Arthur", "Herren > Unterwäsche"), FEED) is None
    assert feeds.to_product(row(2, "Jazz-Pants Modell: Lowcut", "Damen"), FEED) is None
    assert feeds.to_product(row(3, "Boxer Shorts Kenny", ""), FEED) is None
    assert feeds.to_product(row(4, "Kinder Jeans Mini", ""), FEED) is None
    dress = feeds.to_product(row(5, "Satin Slip Dress", "Damen > Kleider"), FEED)
    assert dress and dress.gender == "damen" and dress.category == "Kleider & Röcke"


def test_sizes_of_the_same_item_only_once(monkeypatch):
    rows = [row(n, "Baggy Barrel Leg Jeans Modell: Daybreak", "Damen > Jeans") for n in (1, 2, 3)]
    rows.append(row(4, "Wide Leg Jeans Modell: Dusk", "Damen > Jeans"))
    monkeypatch.setattr(feeds, "download", lambda url: b"")
    monkeypatch.setattr(feeds, "read_rows", lambda data: rows)
    result = feeds.import_feed({**FEED, "url": "https://x"})
    assert [p.name for p in result["products"]] == ["Baggy Barrel Leg Jeans Modell: Daybreak",
                                                    "Wide Leg Jeans Modell: Dusk"]


def test_shop_shows_women_or_men_like_the_pins(client, monkeypatch):
    from backend import products, storage
    from backend.products import Product

    def item(n, gender):
        return Product(id=f"f-{n}", name=f"Jeans {n}", shop="S", price=40, category="Hosen",
                       image_url="https://i/x.jpg", affiliate_url="https://a/x", gender=gender)

    class Source:
        def load(self):
            return [item(1, "damen"), item(2, "herren"), item(3, None)]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "Damen Jeans Outfit"}]})
    ids = lambda q="": sorted(p["id"] for p in client.get(f"/api/recommendations?{q}").json()["products"])
    assert ids() == ["f-1", "f-3"]                        # Pins: Damen -> keine Herrenteile
    assert ids("gender=herren") == ["f-2", "f-3"]
    assert ids("gender=alle") == ["f-1", "f-2", "f-3"]


def test_car_parts_and_fake_discounts_are_not_shown():
    assert feeds.to_product(row(6, "Plastic Fuel Line Connector Joint 70x30mm Hose Adapter"), FEED) is None
    assert feeds.to_product(row(7, "594061 Durable Fit For Briggs & Stratton Replacement Cap"), FEED) is None
    assert feeds.to_product(row(8, "Exotic Strappy Lace Bodysuit - Sexy Teddy Nightwear Lingerie"), FEED) is None
    assert feeds.to_product(row(9, "Damen Gartenschlauch? nein: Weite Hose Leinen", "Damen > Hosen"), FEED)
    from backend.products import sale_price
    assert sale_price(10, 20) == 20          # −50 %: echt
    assert sale_price(7.42, 67.49) is None   # −89 %: erfundener Originalpreis


def test_old_imports_are_redone_automatically(fake, monkeypatch):
    from backend import storage
    storage.write_json(feeds.STORE_FILE, {"fetched_at": 9e12, "version": 1, "feeds": {}})
    calls = []
    monkeypatch.setattr(feeds, "refresh_in_background", lambda: calls.append(1))
    feeds.FeedProductSource().load()
    assert calls


def test_cheap_spam_and_unreadable_titles_never_enter_the_shop():
    cheap = row(10, "Damen Bluse Basic", "Damen > Oberteile")
    cheap["search_price"] = "4.50"
    assert feeds.to_product(cheap, FEED) is None                                  # unter 8 € Top
    assert feeds.to_product(row(11, "Hot Sale 2025 New Women Jeans"), FEED) is None
    assert feeds.to_product(row(12, "Spodnie damskie szerokie dżinsy"), FEED) is None   # Polnisch
    assert feeds.to_product(row(13, "Women Jeans " + "Casual Summer Loose " * 6), FEED) is None
    pln = row(14, "Women Wide Leg Jeans", "Jeans")
    pln.update(search_price="30", currency="PLN")                                 # ≈ 7 € Jeans
    assert feeds.to_product(pln, FEED) is None
    assert feeds.to_product(row(15, "Women Wide Leg Jeans", "Jeans"), FEED)       # 30 € ok


def test_only_items_that_fit_the_pins_are_shown(client, monkeypatch):
    from backend import products, storage
    from backend.products import Product

    def item(n, category, colors=(), styles=()):
        return Product(id=f"f-{n}", name=f"Teil {n}", shop="S", price=40, category=category,
                       colors=list(colors), style_tags=list(styles),
                       image_url="https://i/x.jpg", affiliate_url="https://a/x")

    class Source:
        def load(self):
            return [item(1, "Oberteile", ["beige"]),                 # Hoodie wie in den Pins
                    item(2, "Hosen", ["schwarz"]),                   # passt gar nicht
                    item(3, "Hosen", ["beige"]),                     # nur die Farbe -> zu wenig
                    item(4, "Jacken", ["beige"], ["oversized"])]     # Farbe + Stil

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "beige oversized hoodie outfit"}]})
    data = client.get("/api/recommendations?gender=alle").json()
    assert sorted(p["id"] for p in data["products"]) == ["f-1", "f-4"]
    assert data["unfitting"] == 2
