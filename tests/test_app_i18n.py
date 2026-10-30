"""App auf Deutsch und Englisch (backend/i18n.py, frontend/i18n.js, frontend/i18n/en.json).

Schlägt ein Test hier fehl, fehlt eine Übersetzung: den deutschen Text (genau wie im Code)
links und Englisch rechts in frontend/i18n/en.json eintragen.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import i18n, vibe
from backend.main import app
from scripts import i18n as page_i18n

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
APP_PAGES = ["index", "shop", "produkt", "konto", "merkliste", "foto", "stile"]
APP_SCRIPTS = ["shop", "produkt", "konto", "merkliste", "foto", "feedback", "analysis", "vibecard",
               "fitcard", "share", "nav"]
DICT = i18n.dictionary()
_, SAME = page_i18n.load()


def _keys(pattern: str, text: str) -> set[str]:
    return {" ".join(m.split()) for m in re.findall(pattern, text)}


@pytest.mark.parametrize("page", APP_PAGES)
def test_every_text_on_app_pages_is_translated(page):
    texts = page_i18n.texts((FRONTEND / f"{page}.html").read_text("utf-8"))
    assert sorted({t for t in texts if t not in DICT and t not in SAME}) == []


@pytest.mark.parametrize("script", APP_SCRIPTS)
def test_every_t_call_in_scripts_is_translated(script):
    source = (FRONTEND / f"{script}.js").read_text("utf-8")
    # t("…") auch über mehrere Zeilen: t("Teil 1 " + "Teil 2")
    calls = re.findall(r'\bt\(\s*((?:"(?:[^"\\]|\\.)*"\s*\+?\s*)+)', source)
    keys = {" ".join("".join(re.findall(r'"((?:[^"\\]|\\.)*)"', c)).split()) for c in calls}
    assert sorted(k for k in keys if k and k not in DICT) == []


def test_every_backend_tr_call_is_translated():
    missing = []
    for path in (Path(__file__).resolve().parent.parent / "backend").glob("*.py"):
        for call in re.findall(r'\btr\(\s*((?:"[^"]*"\s*)+)', path.read_text("utf-8")):
            key = " ".join("".join(re.findall(r'"([^"]*)"', call)).split())
            if key not in DICT:
                missing.append(f"{path.name}: {key}")
    assert missing == []


def test_every_vibe_line_is_translated():
    lines = [line for v in vibe.VIBES + [vibe.UNIQUE, vibe.NO_PINS] for line in v.lines]
    assert [line for line in lines if " ".join(line.split()) not in DICT] == []


def test_language_choice():
    assert i18n.choose("lang=en; other=1", "de-AT") == "en"           # Cookie gewinnt
    assert i18n.choose("", "de-AT,de;q=0.9") == "de"
    assert i18n.choose("", "fr-FR,fr;q=0.9") == "en"                   # alles andere: Englisch
    assert i18n.choose("lang=xx", "") == "de"
    assert i18n.tr("{n} Teile · zusammen {total}", "en", n=2, total="€5") == "2 items · €5 in total"


def test_api_speaks_the_chosen_language(fake):
    client = TestClient(app, cookies={"lang": "en"})
    assert client.get("/api/products/gibt-es-nicht").json()["detail"] == "Product not found."
    vibe_en = client.get("/api/vibe").json()
    assert vibe_en["title"] == "Still a mystery" and "Connect Pinterest" in vibe_en["text"]
    german = TestClient(app, headers={"Accept-Language": "de-AT"})
    assert german.get("/api/products/gibt-es-nicht").json()["detail"] == "Produkt nicht gefunden."
    script = client.get("/i18n-en.js")
    assert script.status_code == 200 and script.text.startswith("window.MALIPIN_EN = {")


GERMAN = re.compile(r"[äöüßÄÖÜ]|\b(ich|du|dein\w*|nicht|und|ist|mit|zum|der|die|das|ein|eine|noch|"
                    r"hier|dir|mir|keine?|wir|uns|auf|von|aus|bitte|schon|fertig|merk\w*)\b")


@pytest.mark.parametrize("script", APP_SCRIPTS)
def test_german_sentences_in_scripts_are_in_the_dictionary(script):
    """Deutsche Sätze, die JavaScript anzeigt, übersetzt i18n.js automatisch – wenn sie im
    Wörterbuch stehen. Code-Kommentare zählen nicht."""
    source = re.sub(r"^\s*//.*$|/\*.*?\*/", "", (FRONTEND / f"{script}.js").read_text("utf-8"),
                    flags=re.MULTILINE | re.DOTALL)
    literals = {" ".join(m.split()) for m in re.findall(r'"((?:[^"\\\n]|\\.)*)"', source)}
    german = {s for s in literals if GERMAN.search(s) and not s.startswith(("/", "."))}
    assert sorted(s for s in german if s not in DICT and s not in SAME) == []


def test_pinterest_coming_soon_when_closed(client, monkeypatch):
    monkeypatch.setenv("PINTEREST_OPEN", "0")
    assert client.get("/api/features").json() == {"pinterest": False}
    response = client.get("/auth/login", follow_redirects=False)
    assert response.headers["location"] == "/konto.html?bald=1"
    monkeypatch.delenv("PINTEREST_OPEN")
    assert client.get("/api/features").json() == {"pinterest": True}


def test_legal_pages_served_by_the_app(client):
    assert "Impressum" in client.get("/impressum.html").text
    assert "Privacy Policy" in client.get("/datenschutz.html").text
    assert "Privacy Policy" in client.get("/privacy.html").text
    assert 'href="/impressum.html"' in client.get("/").text
