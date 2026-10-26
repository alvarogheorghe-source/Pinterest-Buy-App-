"""Malipin Picks (backend/picks.py) + Admin-Seite."""

import pytest
from fastapi.testclient import TestClient

from backend import storage
from backend.main import app

PICK = {"name": "Leinenhemd Oversized Beige", "seller": "LinenStudio", "price": 29.9,
        "department": "mode", "category": "Oberteile",
        "url": "https://shop.example/leinenhemd", "image_url": "https://shop.example/hemd.jpg",
        "note": "Geprüft: echte Fotos, Versand in die EU, Rückgabe 30 Tage. Cozy Basic."}


@pytest.fixture
def admin(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "geheim-123")
    monkeypatch.setattr("backend.main.time.sleep", lambda s: None)   # Test nicht bremsen
    assert client.post("/api/admin/login", json={"password": "geheim-123"}).status_code == 200
    return client


def test_admin_is_off_without_password(fake, client, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert client.post("/api/admin/login", json={"password": "x"}).status_code == 404
    assert client.get("/api/admin/picks").status_code == 404


def test_wrong_password_and_not_logged_in(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "geheim-123")
    monkeypatch.setattr("backend.main.time.sleep", lambda s: None)
    assert client.post("/api/admin/login", json={"password": "falsch"}).status_code == 401
    assert client.get("/api/admin/picks").status_code == 401
    assert client.post("/api/admin/picks", json=PICK).status_code == 401


def test_add_pick_detects_colors_and_styles(admin):
    pick = admin.post("/api/admin/picks", json=PICK).json()
    assert pick["id"].startswith("pick-") and pick["pick"] is True
    assert pick["shop"] == "Malipin Pick · LinenStudio"
    assert pick["colors"] == ["beige"] and set(pick["style_tags"]) >= {"oversized", "cozy"}
    assert pick["sponsored"] is False
    assert [p["id"] for p in admin.get("/api/admin/picks").json()] == [pick["id"]]


@pytest.mark.parametrize("change,message", [
    ({"url": "http://unsicher.example"}, "https"),
    ({"category": "Leuchten"}, "Welt"),                       # Wohnen-Kategorie bei Mode
    ({"name": "Nike Style Hoodie"}, "Marke"),                 # Fälschungs-Filter gilt auch hier
])
def test_pick_checks(admin, change, message):
    response = admin.post("/api/admin/picks", json={**PICK, **change})
    assert response.status_code in (400, 422) and message.lower() in response.text.lower()


def test_picks_in_the_shop_with_bonus_and_filter(admin):
    pick_id = admin.post("/api/admin/picks", json=PICK).json()["id"]
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": str(i), "title": "beige oversized cozy top"} for i in range(3)]})
    products = admin.get("/api/recommendations?department=mode").json()["products"]
    assert products[0]["id"] == pick_id                       # passt + kleiner Vorrang
    only = admin.get("/api/recommendations?department=mode&picks_only=true").json()["products"]
    assert [p["id"] for p in only] == [pick_id]
    # ♡ und Detailseite funktionieren
    assert admin.post("/api/feedback", json={"product_id": pick_id, "vote": "like"}).status_code == 200
    assert admin.get(f"/api/products/{pick_id}").json()["product"]["pick_note"].startswith("Geprüft")


def test_picks_are_the_same_for_everyone(admin, monkeypatch):
    pick_id = admin.post("/api/admin/picks", json=PICK).json()["id"]
    monkeypatch.setenv("MULTI_USER", "1")
    visitor = TestClient(app)
    ids = [p["id"] for p in visitor.get("/api/recommendations?department=mode").json()["products"]]
    assert pick_id in ids
    assert visitor.get("/api/admin/picks").status_code == 401  # Besucher sind kein Admin


def test_edit_and_delete(admin):
    pick_id = admin.post("/api/admin/picks", json=PICK).json()["id"]
    edited = admin.put(f"/api/admin/picks/{pick_id}", json={**PICK, "price": 24.0}).json()
    assert edited["price"] == 24.0 and edited["id"] == pick_id
    assert admin.delete(f"/api/admin/picks/{pick_id}").status_code == 200
    assert admin.get("/api/admin/picks").json() == []
    assert admin.delete(f"/api/admin/picks/{pick_id}").status_code == 404
