"""Tests für die Merkliste (GET /api/saved).

Starten mit:  pytest -v
"""

from backend import feedback, storage


def like(product_id, at):
    votes = feedback.load_feedback()
    votes[product_id] = {"vote": "like", "at": at}
    storage.write_json(feedback.FEEDBACK_FILE, votes)


def test_empty_merkliste(fake, client):
    assert client.get("/api/saved").json() == []


def test_only_liked_products_newest_first(fake, client):
    like("prod-001", at=100)          # Oversized Hoodie (Mode)
    like("prod-031", at=300)          # Keramikvase (Wohnen)
    like("prod-005", at=200)          # Strickpullover (Mode)
    client.post("/api/feedback", json={"product_id": "prod-010", "vote": "dislike"})

    saved = client.get("/api/saved").json()
    assert [p["id"] for p in saved] == ["prod-031", "prod-005", "prod-001"]
    assert saved[0]["name"] == "Keramikvase Sand" and saved[0]["vote"] == "like"


def test_filter_by_department(fake, client):
    like("prod-001", at=1)
    like("prod-031", at=2)
    assert [p["id"] for p in client.get("/api/saved?department=wohnen").json()] == ["prod-031"]
    assert [p["id"] for p in client.get("/api/saved?department=mode").json()] == ["prod-001"]


def test_unliking_removes_from_merkliste(fake, client):
    client.post("/api/feedback", json={"product_id": "prod-001", "vote": "like"})
    assert len(client.get("/api/saved").json()) == 1
    client.post("/api/feedback", json={"product_id": "prod-001", "vote": None})
    assert client.get("/api/saved").json() == []


def test_merkliste_page_exists(client):
    assert client.get("/merkliste.html").status_code == 200
