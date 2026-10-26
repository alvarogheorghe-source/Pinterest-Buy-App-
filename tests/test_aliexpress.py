"""AliExpress (backend/aliexpress.py) + Fälschungs-Filter (backend/counterfeit.py) – simuliert."""

from urllib.parse import parse_qs

import httpx
import pytest

from backend import aliexpress, storage
from backend.counterfeit import looks_like_fake


def offer(pid, title, price="19.90", currency="EUR"):
    return {"product_id": pid, "product_title": title, "target_sale_price": price,
            "target_sale_price_currency": currency,
            "product_main_image_url": f"https://ae01.alicdn.com/{pid}.jpg",
            "promotion_link": f"https://s.click.aliexpress.com/e/{pid}"}


class FakeAliExpress:
    """Spielt die Open Platform: prüft die Signatur wie der echte Server."""

    def __init__(self):
        self.queries = []
        self.results = {}
        self.secret = "secret"

    def handler(self, request: httpx.Request) -> httpx.Response:
        params = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        signature = params.pop("sign")
        if signature != aliexpress.sign(params, self.secret):
            return httpx.Response(200, json={"error_response": {"code": "IncompleteSignature"}})
        self.queries.append(params["keywords"])
        assert params["target_currency"] == "EUR" and params["tracking_id"] == "malipin"
        products = self.results.get(params["keywords"], [])
        return httpx.Response(200, json={"aliexpress_affiliate_product_query_response": {
            "resp_result": {"resp_code": 200, "result": {"products": {"product": products}}}}})


@pytest.fixture
def fake_ali(fake, monkeypatch):
    monkeypatch.setenv("PRODUCT_SOURCE", "")
    for name in ("EBAY_CLIENT_ID", "ETSY_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ALIEXPRESS_APP_KEY", "key")
    monkeypatch.setenv("ALIEXPRESS_APP_SECRET", "secret")
    monkeypatch.setenv("ALIEXPRESS_TRACKING_ID", "malipin")
    api = FakeAliExpress()
    transport = httpx.MockTransport(api.handler)
    monkeypatch.setattr(aliexpress, "_http", lambda: httpx.Client(transport=transport))
    return api


@pytest.mark.parametrize("title,fake_or_brand", [
    ("Nike Air Force 1 Sneaker", True), ("1:1 Replica Bag", True), ("Adidas-style Samba", True),
    ("Converse Style Canvas Sneaker", True), ("Oversized Hoodie Beige", False),
    ("Retro Sneakers Gum Sole Unisex", False), ("Baggy Wide Leg Jeans", False),
])
def test_counterfeit_filter(title, fake_or_brand):
    assert looks_like_fake(title) is fake_or_brand


def test_only_brandless_items_in_the_shop(fake_ali, client):
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [
        {"id": "1", "title": "beige oversized hoodie"},
        {"id": "2", "title": "adidas samba sneakers", "image_brands": ["Adidas Samba"]}]})
    fake_ali.results["beige oversized sweater"] = [
        offer("1001", "Beige Oversized Hoodie Unisex"),
        offer("1002", "Nike Oversized Hoodie Beige"),            # Marke -> raus
        offer("1003", "Oversized Sweater Beige", currency="USD"),  # keine Euro -> raus
    ]
    data = client.get("/api/recommendations?department=mode").json()
    assert data["sources"] == ["aliexpress"]
    assert [p["id"] for p in data["products"]] == ["aliexpress-1001"]
    product = data["products"][0]
    assert product["sponsored"] is True and product["shop"] == "AliExpress"   # Werbung
    assert all("samba" not in q.lower() for q in fake_ali.queries)            # nie nach Marken suchen


def test_wrong_keys_clear_message(fake_ali, client):
    fake_ali.secret = "anderes"                                   # Signatur passt nicht
    storage.save_pins({"fetched_at": 1, "board_ids": ["x"], "pins": [{"id": "1", "title": "hoodie"}]})
    response = client.get("/api/recommendations")
    assert response.status_code == 500 and "ALIEXPRESS_APP_KEY" in response.json()["detail"]
