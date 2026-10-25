# Style App (Prototyp)

Eine Webapp, die sich mit deinem Pinterest-Konto verbindet, aus deinen Boards deinen
Stil ableitet und passende Kleidung aus Partnershops vorschlägt.

**Stand:** Phase 1 fertig (Projektgerüst, Pinterest-Login mit Board-Auswahl, Pins laden, Produktdaten, Matching, Shop-Oberfläche).

## Aufbau

```
backend/
  main.py       FastAPI-App: Routen für Login, Boards, Auswahl; liefert das Frontend aus
  config.py     liest Einstellungen aus .env
  pinterest.py  OAuth 2.0 + Pinterest API v5 (Login, Token-Refresh, Boards)
  pins.py       lädt die Pins der ausgewählten Boards (max. 250 pro Board)
  matching.py   Stilprofil aus Pin-Texten + Produkt-Ranking mit Begründung
  shop_links.py erkennt Pins mit Link zu Shops/Second-Hand (Depop, Vinted …)
  prices.py     liest Preise aus Pin-Texten („25€“, „£18“ …)
  demo_pins.py  schreibt Beispiel-Pins, um ohne Pinterest-Login zu testen
  products.py   Produktmodell, austauschbare Produktquelle, Preis-/Kategoriefilter
  storage.py    speichert Daten als JSON in data/
frontend/
  index.html + shop.js    Shop: Stilprofil, Filter, Produktraster
  konto.html + konto.js   Mein Pinterest: verbinden, Boards wählen, Pins laden
  style.css               gemeinsames Design (Farben als Variablen ganz oben)
data/           products.json (Beispielprodukte) + Laufzeitdaten (tokens.json etc. – nicht im Git)
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

Dann http://localhost:8000 öffnen → **Mein Pinterest** → „Mit Pinterest verbinden“ → Boards auswählen → speichern → „Pins laden“ → „Passende Produkte ansehen“.

Die Pins landen in `data/pins.json` (Titel, Beschreibung, Bild-URL, Hauptfarbe).

- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:8000/docs → automatische API-Doku von FastAPI (zum Ausprobieren)

## Produkte

`data/products.json` enthält 30 **erfundene** Produkte (Shops, Preise und Links sind nicht echt).
Farben und Stil-Tags sind feste, kleingeschriebene Begriffe (`beige`, `streetwear` …).

- http://localhost:8000/api/products – alle Produkte
- http://localhost:8000/api/products?max_price=30&category=Hosen – gefiltert
- http://localhost:8000/api/categories – alle Kategorien

**Echten Affiliate-Feed einbinden (später):** In `backend/products.py` eine neue Klasse
schreiben, die von `ProductSource` erbt und in `load()` den Feed in `Product`-Objekte
umwandelt. Dann in `get_product_source()` diese Klasse zurückgeben – der Rest der App
bleibt unverändert.

## Shop-Oberfläche

- Kachelraster mit Bild, Shop, Name, Preis und Begründung; auf dem Handy 2 Spalten
- Filter: Budget (bis 15/25/40/60 €), Kategorie, Sortierung (Passung oder Preis)
- „Zum Shop“ öffnet den Affiliate-Link im neuen Tab (`rel="sponsored noopener"`),
  daneben die Kennzeichnung **Werbung**; im Footer ein Werbehinweis
- Links in Produktdaten müssen mit `http(s)://` beginnen (Schutz vor `javascript:`-Links)

## Tab „Aus meinen Pins“

Viele bewerben ihre Kleidung (z.B. ihren Depop-Shop) auf Pinterest. Führt ein Pin
direkt zu einem Angebot, ist das genau das Teil aus dem Bild.

- `shop_links.py` prüft den Ziel-Link jedes Pins: Second Hand (Depop, Vinted, willhaben,
  eBay, Kleinanzeigen, Etsy, Sellpy), Shops (Zalando, ASOS, H&M, Zara, About You) und
  unbekannte Shops mit Produkt-Adresse (`/products/…`). Social Media, gefälschte
  Adressen (`depop.com.betrug.net`) und Nicht-Web-Links werden ignoriert.
  Neue Plattform = eine Zeile in `PLATFORMS`.
- `prices.py` liest den ersten Preis mit Währung aus Titel/Beschreibung („ca. 25 €“).
- Budgetfilter blendet nur aus, was sicher zu teuer ist (ohne Preis / £ / $ bleibt sichtbar).
- Diese Links sind **keine Werbung** (wir verdienen nichts) → Hinweis „Link aus deinem Pin“,
  `rel="nofollow"`. Shop-Seiten werden nicht abgerufen (kein Scraping).
- http://localhost:8000/#pins öffnet den Tab direkt; API: `/api/pin-items?max_price=30`

## Matching (ohne KI)

1. In Titel + Beschreibung jedes Pins werden Farb- und Stilwörter gesucht (Deutsch + Englisch,
   Synonyme in `COLOR_SYNONYMS` / `STYLE_SYNONYMS` in `backend/matching.py`).
2. Jeder Begriff zählt höchstens einmal pro Pin → Stilprofil, z.B. „beige in 7 von 12 Pins“.
3. Produkte bekommen Punkte für jede passende Farbe/jeden Stil (häufige Begriffe zählen mehr).
   Bei Gleichstand gewinnt das günstigere Produkt.

- http://localhost:8000/api/profile – dein Stilprofil
- http://localhost:8000/api/recommendations?max_price=40 – Empfehlungen mit Begründung

**Ohne Pinterest-Login testen:** `python -m backend.demo_pins` schreibt 12 Beispiel-Pins
nach `data/pins.json`. Echte Pins („Pins laden“) überschreiben sie.

**Phase 2:** `build_style_profile()` durch eine Bilderkennung ersetzen, die dasselbe
`StyleProfile` liefert – `rank_products()` bleibt gleich.

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
