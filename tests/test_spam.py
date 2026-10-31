"""Schutz vor Spam und Passwort-Raten (Grenzen pro IP, backend/rate_limit.py)."""

from backend import stats


def test_admin_password_guessing_is_stopped(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "richtig-langes-passwort")
    monkeypatch.setattr("time.sleep", lambda s: None)          # Test nicht ausbremsen
    codes = [client.post("/api/admin/login", json={"password": f"falsch{i}"}).status_code
             for i in range(6)]
    assert codes == [401] * 5 + [429]
    # Auch das richtige Passwort hilft dann erst nach der Pause
    assert client.post("/api/admin/login",
                       json={"password": "richtig-langes-passwort"}).status_code == 429


def test_fake_visits_cannot_flood_the_stats(fake, client):
    for _ in range(320):
        client.post("/api/hit", json={"type": "click", "url": "https://shop.example/x"})
    assert stats.summary()["totals"]["clicks"] == 300


def test_feedback_rejects_silly_input(fake, client):
    assert client.post("/api/feedback", json={"product_id": "x" * 500, "vote": "like"}).status_code == 422
    assert client.post("/api/feedback", json={"product_id": "", "vote": "like"}).status_code == 422
    assert client.post("/api/feedback", json={"product_id": "prod-001", "vote": "hate"}).status_code == 422
