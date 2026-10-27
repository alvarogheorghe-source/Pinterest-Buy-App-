"""Geprüfte Shops (backend/shops.py) + Admin-Seite – eBay wird simuliert."""

import pytest
from fastapi.testclient import TestClient

from backend import aliexpress, shops
from backend.main import app
from backend.shops import ShopInput
from tests.test_ebay import fake_ebay, item, save_pins  # noqa: F401  (Fixture)

SHOP = {"platform": "ebay", "seller": "Vintage_Wien", "name": "Vintage Wien",
        "note": "Geprüft: 99 % positive Bewertungen, Versand aus Österreich."}


def ebay_item(item_id, title, seller, price="24.99"):
    return {**item(item_id, title, price=price), "seller": {"username": seller}}


@pytest.fixture
def admin(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "geheim-123")
    monkeypatch.setattr("backend.main.time.sleep", lambda s: None)   # Test nicht bremsen
    assert client.post("/api/admin/login", json={"password": "geheim-123"}).status_code == 200
    return client


def test_admin_is_off_without_password(fake, client, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert client.post("/api/admin/login", json={"password": "x"}).status_code == 404
    assert client.get("/api/admin/shops").status_code == 404


def test_wrong_password_and_not_logged_in(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "geheim-123")
    monkeypatch.setattr("backend.main.time.sleep", lambda s: None)
    assert client.post("/api/admin/login", json={"password": "falsch"}).status_code == 401
    assert client.get("/api/admin/shops").status_code == 401
    assert client.post("/api/admin/shops", json=SHOP).status_code == 401


def test_add_list_duplicate_delete(admin):
    shop = admin.post("/api/admin/shops", json=SHOP).json()
    assert shop["id"].startswith("shop-")
    assert [s["id"] for s in admin.get("/api/admin/shops").json()] == [shop["id"]]
    # Gleicher Verkäufer (Groß/klein egal) -> abgelehnt
    again = admin.post("/api/admin/shops", json={**SHOP, "seller": "vintage_wien"})
    assert again.status_code == 400 and "schon" in again.text
    assert admin.post("/api/admin/shops", json={**SHOP, "platform": "zalando"}).status_code == 422
    assert admin.delete(f"/api/admin/shops/{shop['id']}").json() == {"ok": True}
    assert admin.delete(f"/api/admin/shops/{shop['id']}").status_code == 404
    assert admin.get("/api/admin/shops").json() == []


def test_all_offers_of_a_trusted_shop_get_badge_bonus_and_filter(admin, fake_ebay):
    admin.post("/api/admin/shops", json=SHOP)
    save_pins("beige oversized hoodie", "beige hoodie")
    fake_ebay.results["beige oversized Pullover"] = [
        ebay_item("10", "Beige Oversized Hoodie Damen", "irgendwer", price="19.90"),
        ebay_item("11", "Beige Oversized Hoodie Damen", "VINTAGE_WIEN", price="29.90"),
        ebay_item("12", "Beiger Rollkragen Pullover Damen", "Vintage_Wien"),
    ]
    products = admin.get("/api/recommendations?department=mode").json()["products"]
    assert products[0]["id"] == "ebay-11"          # gleich passend, teurer – aber geprüft
    assert products[0]["trusted"] and products[0]["seller"] == "VINTAGE_WIEN"
    assert not next(p for p in products if p["id"] == "ebay-10")["trusted"]
    only = admin.get("/api/recommendations?department=mode&trusted_only=true").json()["products"]
    assert {p["id"] for p in only} == {"ebay-11", "ebay-12"}
    detail = admin.get("/api/products/ebay-12").json()["product"]
    assert detail["trusted_note"].startswith("Geprüft")


def test_shops_are_the_same_for_everyone(admin, fake_ebay, monkeypatch):
    admin.post("/api/admin/shops", json=SHOP)
    monkeypatch.setenv("MULTI_USER", "1")
    visitor = TestClient(app)
    assert shops.is_trusted("ebay", "vintage_wien")
    assert visitor.get("/api/admin/shops").status_code == 401   # Besucher sind kein Admin


def test_aliexpress_official_store_may_show_brands(fake):
    offer = {"product_id": "1", "product_title": "adidas Originals Hoodie", "shop_id": 777,
             "target_sale_price": "39.90", "target_sale_price_currency": "EUR",
             "product_main_image_url": "https://ae01.alicdn.com/1.jpg",
             "promotion_link": "https://s.click.aliexpress.com/e/1"}
    assert aliexpress.to_product(offer, "mode", "Oberteile") is None       # sonst: Fake-Filter
    shops.add(ShopInput(platform="aliexpress", seller="777", name="adidas Official Store"))
    product = aliexpress.to_product(offer, "mode", "Oberteile")
    assert product and product.seller == "777"
