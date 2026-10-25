# Style App (Prototyp)

Eine Webapp, die sich mit deinem Pinterest-Konto verbindet, aus deinen Boards deinen
Stil ableitet und passende Kleidung aus Partnershops vorschlägt.

**Stand:** Phase 1, Schritt 1–3 (Projektgerüst, Pinterest-Login mit Board-Auswahl, Pins laden).

## Aufbau

```
backend/
  main.py       FastAPI-App: Routen für Login, Boards, Auswahl; liefert das Frontend aus
  config.py     liest Einstellungen aus .env
  pinterest.py  OAuth 2.0 + Pinterest API v5 (Login, Token-Refresh, Boards)
  pins.py       lädt die Pins der ausgewählten Boards (max. 250 pro Board)
  storage.py    speichert Daten als JSON in data/
frontend/       index.html, style.css, app.js
data/           Laufzeitdaten (tokens.json etc. – nicht im Git)
tests/          pytest-Tests; conftest.py simuliert den Pinterest-Server
```

## Einrichten

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # danach .env ausfüllen (siehe unten)
```

### Werte für `.env`

1. Auf https://developers.pinterest.com mit einem **Business-Konto** einloggen
   (ein normales Konto lässt sich kostenlos umwandeln).
2. **My Apps → Connect app** und App anlegen.
3. In der App findest du die **App ID** → `PINTEREST_CLIENT_ID`
   und den **App secret key** → `PINTEREST_CLIENT_SECRET`.
4. In den App-Einstellungen unter **Redirect URIs** genau
   `http://localhost:8000/auth/callback` eintragen.
5. `SESSION_SECRET` selbst erzeugen:
   `python -c "import secrets; print(secrets.token_hex(32))"`

Neue Apps haben oft nur „Trial Access“. Für dein eigenes Konto reicht das meist.

## Starten

```bash
uvicorn backend.main:app --reload
```

Dann http://localhost:8000 öffnen → „Mit Pinterest verbinden“ → Boards auswählen → speichern → „Pins laden“.

Die Pins landen in `data/pins.json` (Titel, Beschreibung, Bild-URL, Hauptfarbe).

- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:8000/docs → automatische API-Doku von FastAPI (zum Ausprobieren)

## Testen

```bash
pytest -v
```

Die Tests brauchen keine echten Zugangsdaten, Pinterest wird simuliert.

## Wie der Login funktioniert (OAuth 2.0)

1. `/auth/login` schickt dich zu Pinterest. Du loggst dich **dort** ein, unsere App sieht dein Passwort nie.
2. Pinterest schickt dich zu `/auth/callback?code=...&state=...` zurück.
3. Der `state` muss zu dem passen, was wir im Session-Cookie gemerkt haben (Schutz vor gefälschten Logins).
4. Den `code` tauschen wir gegen einen **Access Token** (30 Tage gültig) und einen **Refresh Token**.
5. Läuft der Access Token in < 1 Tag ab, holt `pinterest.py` automatisch einen neuen.
   Ist auch der Refresh Token ungültig, musst du dich neu verbinden.

## Sicherheit

- Geheime Schlüssel stehen nur in `.env`, und `.env` steht in `.gitignore`.
- Gespeichert werden nur OAuth-Tokens (`data/tokens.json`, ebenfalls ignoriert), keine Passwörter oder Cookies.
- Kein Scraping, nur die offizielle API mit Lese-Rechten.
- Prototyp für **einen** Nutzer lokal. Für eine echte Mehrnutzer-App braucht es später
  eine Datenbank mit Tokens pro Nutzer (verschlüsselt).
