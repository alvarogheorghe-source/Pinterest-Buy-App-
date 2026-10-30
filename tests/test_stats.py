"""Besucherzählung ohne Cookies (backend/stats.py)."""

from backend import stats

BROWSER = {"User-Agent": "Mozilla/5.0 (iPhone)"}


def test_counts_views_visitors_clicks_without_cookies(fake, client):
    for page in ("/shop.html", "/shop.html", "/stile.html"):
        assert client.post("/api/hit", json={"type": "view", "page": page}, headers=BROWSER).status_code == 204
    client.post("/api/hit", json={"type": "view", "page": "/x"}, headers={"User-Agent": "Googlebot/2.1"})
    client.post("/api/hit", json={"type": "click", "url": "https://www.ebay.de/itm/1?campid=5"},
                headers=BROWSER)
    client.post("/api/hit", json={"type": "click", "url":
                "https://go.skimresources.com/?id=1&xs=1&url=https%3A%2F%2Fwww.zara.com%2Fde%2Fx"},
                headers=BROWSER)

    summary = stats.summary()
    day = summary["days"][-1]
    assert summary["totals"] == {"views": 3, "visitors": 1, "clicks": 2, "photos": 0}
    assert day["pages"] == {"/shop.html": 2, "/stile.html": 1}
    assert dict(summary["top_shops"]) == {"ebay.de": 1, "zara.com": 1}
    stored = str(stats.storage.read_json(stats.STATS_FILE))
    assert "testclient" not in stored and "iPhone" not in stored   # keine IP, kein Browser


def test_admin_stats_need_login(fake, client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "geheim")
    assert client.get("/api/admin/stats").status_code == 401
    client.post("/api/admin/login", json={"password": "geheim"})
    assert client.get("/api/admin/stats").json()["totals"]["views"] == 0


def test_bad_hit_is_rejected(fake, client):
    assert client.post("/api/hit", json={"type": "delete"}).status_code == 422


def test_where_visitors_come_from():
    from backend.stats import source_of
    assert source_of("TikTok") == "tiktok"                                   # ?von=tiktok
    assert source_of("<script>") == "script"                                 # nur harmlose Zeichen
    assert source_of("", "https://l.instagram.com/?u=x") == "instagram"
    assert source_of("", "https://www.google.at/") == "google"
    assert source_of("", "https://www.reddit.com/r/x") == "reddit"           # nicht "x" wegen t.co
    assert source_of("", "https://t.co/abc") == "x"
    assert source_of("", "https://modeblog.example/post") == "modeblog.example"
    assert source_of("", "", "Mozilla/5.0 ... Instagram 300.0") == "instagram"   # In-App-Browser
    assert source_of("", "", "Mozilla/5.0 ... musical_ly_2023") == "tiktok"
    assert source_of("", "https://malipin.com/shop.html", "Mozilla", "malipin.com") == "direkt"
    assert source_of("", "", "Mozilla/5.0") == "direkt"


def test_sources_are_counted_once_per_visitor_and_day(fake, client):
    agent = {"User-Agent": "Mozilla/5.0 Instagram"}
    client.post("/api/hit", json={"type": "view", "page": "/", "source": "tiktok"}, headers=agent)
    client.post("/api/hit", json={"type": "view", "page": "/shop.html"}, headers=agent)   # gleiche Person
    client.post("/api/hit", json={"type": "view", "page": "/",
                                  "referrer": "https://www.google.de/"}, headers={"User-Agent": "Mozilla/5.0 B"})
    assert dict(stats.summary()["sources"]) == {"tiktok": 1, "google": 1}
