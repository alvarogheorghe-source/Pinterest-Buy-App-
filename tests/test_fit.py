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
                       colors=["blau"], image_url="https://i/x.jpg", affiliate_url="https://a/x",
                       gender=gender)

    class Source:
        def load(self):
            return [item(1, "damen"), item(2, "herren"), item(3, None)]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "Damen blaue Jeans Outfit"}]})
    ids = lambda q="": sorted(p["id"] for p in client.get(f"/api/recommendations?{q}").json()["products"])
    assert ids() == ["f-1", "f-3"]             # Pins: Damen -> keine Herrenteile (f-3: unklar,
                                               # aber ohne Bildprüfung nicht bestraft)
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
            return [item(1, "Oberteile", ["beige"], ["oversized"]),  # Hoodie wie in den Pins
                    item(2, "Hosen", ["schwarz"]),                   # passt gar nicht
                    item(3, "Hosen", ["beige"]),                     # nur die Farbe -> zu wenig
                    item(4, "Jacken", ["beige"], ["oversized"])]     # Farbe + Stil

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "beige oversized hoodie outfit"}]})
    data = client.get("/api/recommendations?gender=alle").json()
    # f-4: Farbe + Stil, aber Jacken kommen in den Pins nicht vor -> streng: nein
    # (kein Auffüllen mehr – Qualität vor Menge)
    assert sorted(p["id"] for p in data["products"]) == ["f-1"]
    assert data["unfitting"] == 3


def test_image_check_removes_ai_pictures_and_fills_in_gender(client, monkeypatch):
    from backend import product_checks, products, storage
    from backend.products import Product

    def item(n):
        return Product(id=f"c-{n}", name=f"Blaue Jeans {n}", shop="S", price=40, category="Hosen",
                       colors=["blau"], image_url="https://i/x.jpg", affiliate_url="https://a/x")

    class Source:
        def load(self):
            return [item(1), item(2), item(3)]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.write_json(product_checks.CHECKS_FILE, {
        "c-1": {"ai": 0.95, "gender": "herren"},          # KI-Bild -> raus
        "c-2": {"ai": 0.10, "gender": "herren"},          # echt, Herren laut Bild
        "c-3": {"ai": 0.10, "gender": "damen"}})
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "Herren blaue Jeans Outfit"}]})
    data = client.get("/api/recommendations").json()
    assert [p["id"] for p in data["products"]] == ["c-2"]
    assert data["products"][0]["gender"] == "herren"


def test_check_math():
    from backend import product_checks
    photo = {"real": [1.0, 0.0], "ai": [0.0, 1.0]}
    gender = {"herren": [1.0, 0.0], "damen": [0.0, 1.0]}
    result = product_checks.check([0.0, 1.0], photo, gender)
    assert result["ai"] > 0.99 and result["gender"] == "damen"
    unclear = product_checks.check([0.7071, 0.7071], photo, gender)
    assert unclear["gender"] is None and abs(unclear["ai"] - 0.5) < 0.01


def test_etsy_ai_check_is_stricter(fake):
    from backend import product_checks, storage
    storage.write_json(product_checks.CHECKS_FILE, {"etsy-1": {"ai": 0.7}, "ebay-1": {"ai": 0.7}})
    assert product_checks.is_ai("etsy-1") and not product_checks.is_ai("ebay-1")


def test_ebay_first_when_equally_good(client, monkeypatch):
    from backend import products, storage
    from backend.products import Product

    def item(pid):
        return Product(id=pid, name="Blaue Jeans", shop=pid.split("-")[0], price=40,
                       category="Hosen", colors=["blau"], image_url="https://i/x.jpg",
                       affiliate_url="https://a/x")

    class Source:
        def load(self):
            return [item("etsy-1"), item("feed-1"), item("ebay-1")]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [{"id": "1", "title": "blaue Jeans"}]})
    ids = [p["id"] for p in client.get("/api/recommendations?gender=alle").json()["products"]]
    assert ids == ["ebay-1", "feed-1", "etsy-1"]


def test_cut_or_type_against_the_pins_is_never_shown(client, monkeypatch):
    from backend import products, storage
    from backend.products import Product

    def item(pid, name):
        return Product(id=pid, name=name, shop="eBay", price=30, category="Hosen",
                       colors=["schwarz"], image_url="https://i/x.jpg", affiliate_url="https://a/x")

    class Source:
        def load(self):
            return [item("ebay-1", "Schwarze Baggy Jeans"), item("ebay-2", "Schwarze Skinny Jeans"),
                    item("ebay-3", "Schwarze Jeans Shorts Bermuda"), item("ebay-4", "Schwarze Jeans")]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": str(n), "title": "schwarze baggy jeans outfit"} for n in range(4)]})
    data = client.get("/api/recommendations?gender=alle").json()
    ids = [p["id"] for p in data["products"]]
    assert "ebay-2" not in ids and "ebay-3" not in ids       # Skinny / Shorts: Widerspruch
    assert ids[0] == "ebay-1" and "ebay-4" in ids             # Baggy zuerst, ohne Angabe ok


def test_photo_must_roughly_match_the_pins():
    from backend.main import fits_pins
    from backend.matching import StyleProfile
    from collections import Counter
    profile = StyleProfile(pin_count=4, colors=Counter({"schwarz": 4}), categories=Counter({"Hosen": 4}))

    def item(visual, matched, looks=False):
        return {"id": "ebay-1", "category": "Hosen", "matched": matched, "visual": visual,
                "looks_like_pins": looks, "gender": None, "clashes": []}

    assert not fits_pins(item(0.1, ["Hosen", "schwarz"]), profile)        # sieht ganz anders aus
    assert fits_pins(item(0.5, ["Hosen", "schwarz"]), profile)
    assert fits_pins(item(0.7, ["Hosen"], looks=True), profile)           # sieht aus wie die Pins
    assert not fits_pins(item(0.7, ["Hosen"]), profile)                   # ähnlich, aber kein Merkmal
    # Foto noch nicht angeschaut: nur ganz sichere Text-Treffer (Art + zwei typische Merkmale)
    assert not fits_pins(item(None, ["Hosen", "schwarz"]), profile)
    profile.details[("Hosen", "Baggy")] = 4
    assert fits_pins(item(None, ["Hosen", "schwarz", "Baggy"]), profile)


def test_rare_categories_and_one_off_colors_do_not_count():
    from collections import Counter
    from backend.main import fit_check
    from backend.matching import StyleProfile
    profile = StyleProfile(pin_count=30, colors=Counter({"schwarz": 20, "gelb": 1}),
                           styles=Counter({"streetwear": 12}), categories=Counter({"Hosen": 25, "Schuhe": 1}))
    shoe = {"id": "e1", "category": "Schuhe", "matched": ["Schuhe", "schwarz", "streetwear"], "clashes": []}
    assert fit_check(shoe, profile) == (False, "Schuhe kommt in deinen Pins kaum vor")   # 1 von 30
    yellow = {"id": "e2", "category": "Hosen", "matched": ["Hosen", "gelb", "streetwear"], "clashes": []}
    assert not fit_check(yellow, profile)[0]                            # Gelb nur in 1 Pin
    black = {"id": "e3", "category": "Hosen", "matched": ["Hosen", "schwarz", "streetwear"], "clashes": []}
    assert fit_check(black, profile)[0]


def test_luxury_brands_only_when_pinned(client, monkeypatch):
    from backend import products, quality, storage
    from backend.products import Product
    assert quality.luxury_in("GUCCI Ace Sneaker Leder") == {"gucci"}
    assert quality.luxury_in("YSL Tasche") == {"saint laurent"}
    assert quality.luxury_in("Guccio Sneaker") == set()                   # nur ganze Wörter

    def item(pid, name):
        return Product(id=pid, name=name, shop="eBay", price=90, category="Schuhe",
                       colors=["weiß"], image_url="https://i/x.jpg", affiliate_url="https://a/x")

    class Source:
        def load(self):
            return [item("ebay-1", "Gucci Ace Sneaker Weiß"), item("ebay-2", "Weiße Leder Sneaker")]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [{"id": "1", "title": "weiße sneaker"}]})
    assert [p["id"] for p in client.get("/api/recommendations?gender=alle").json()["products"]] == ["ebay-2"]
    storage.save_pins({"fetched_at": 2, "board_ids": ["x"], "pins": [{"id": "1", "title": "gucci weiße sneaker"}]})
    assert "ebay-1" in [p["id"] for p in client.get("/api/recommendations?gender=alle").json()["products"]]


def test_why_page_explains_every_item(client, monkeypatch):
    from backend import products, storage
    from backend.products import Product

    class Source:
        def load(self):
            return [Product(id="e-1", name="Schwarze Baggy Jeans", shop="eBay", price=30, category="Hosen",
                            colors=["schwarz"], image_url="https://i/x.jpg", affiliate_url="https://a/x"),
                    Product(id="e-2", name="Schwarze Skinny Jeans", shop="eBay", price=30, category="Hosen",
                            colors=["schwarz"], image_url="https://i/x.jpg", affiliate_url="https://a/x")]

        def warnings(self):
            return []

    monkeypatch.setattr(products, "get_product_source", lambda: Source())
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": str(n), "title": "schwarze baggy jeans"} for n in range(3)]})
    text = client.get("/api/why").text
    assert "1 von 2 Teilen werden gezeigt" in text
    assert "✓ Schwarze Baggy Jeans" in text and "Widerspruch zu den Pins: Skinny" in text
