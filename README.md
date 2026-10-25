# Style App (Prototyp)

Eine Webapp, die sich mit deinem Pinterest-Konto verbindet, aus deinen Boards deinen
Stil ableitet und passende Kleidung (**Mode**) und Gegenstände (**Wohnen & Deko**) aus
Partnershops und Second Hand vorschlägt.

**Stand:** Phase 1 fertig (Projektgerüst, Pinterest-Login mit Board-Auswahl, Pins laden, Produktdaten, Matching, Shop-Oberfläche).

Was für einen öffentlichen Start noch fehlt (Pinterest-Freigabe, Konten, Hosting,
Recht in Österreich/EU, Affiliate, Kosten): **[docs/LAUNCH.md](docs/LAUNCH.md)**

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
  similar.py    ähnliche Artikel (gleiche Welt, Kategorie, Farben, Stile)
  evaluate.py   misst die Genauigkeit der Vorschläge mit einem Testset
  feedback.py   👍/👎: blendet Dislikes aus, schiebt Ähnliches zu Likes nach oben
  vision.py     Bilderkennung (FashionCLIP): Bild-Vektoren berechnen und vergleichen
  vibe.py       Hoppels Vibe-Check („Goth Baddie 🖤“, „Clean-Girl-Aesthetic 🤍“ …)
eval/           demo_testset.json: Beispiel-Pins mit von Hand gewählten passenden Produkten
  demo_pins.py  schreibt Beispiel-Pins, um ohne Pinterest-Login zu testen
  products.py   Produktmodell, austauschbare Produktquelle, Preis-/Kategoriefilter
  storage.py    speichert Daten als JSON in data/
frontend/
  index.html + landing.css  Startseite: stellt die App vor, „Kostenlos starten“
  shop.html + shop.js     Shop: Stilprofil, Tabs, Filter, Produktraster
  produkt.html + produkt.js  Detailseite mit „Mehr wie das“ (ähnliche Artikel)
  feedback.js             👍/👎-Buttons (Shop und Detailseite)
  bunny.js + bunny.css    Hoppel, das Pixel-Maskottchen (auf allen Seiten)
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

Dann http://localhost:8000 öffnen (Startseite) → **Kostenlos starten** bzw. **Mein Pinterest** → „Mit Pinterest verbinden“ → Boards auswählen → speichern → „Pins laden“ → „Passende Produkte ansehen“ (Shop unter http://localhost:8000/shop.html).

Die Pins landen in `data/pins.json` (Titel, Beschreibung, Bild-URL, Hauptfarbe).

- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:8000/docs → automatische API-Doku von FastAPI (zum Ausprobieren)

## Produkte

`data/products.json` enthält 50 **erfundene** Produkte (Shops, Preise und Links sind nicht echt):
30 × Mode (`"department": "mode"`) und 20 × Wohnen & Deko (`"department": "wohnen"`).
Farben und Stil-Tags sind feste, kleingeschriebene Begriffe (`beige`, `streetwear` …).

- http://localhost:8000/api/products – alle Produkte
- http://localhost:8000/api/products?max_price=30&category=Hosen – gefiltert
- http://localhost:8000/api/products?department=wohnen – nur Wohnen & Deko
- http://localhost:8000/api/categories?department=wohnen – Kategorien einer Welt

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
  Wohn-Shops (IKEA, Westwing, Butlers, JYSK, …), unbekannte Shops mit Produkt-Adresse (`/products/…`). Social Media, gefälschte
  Adressen (`depop.com.betrug.net`) und Nicht-Web-Links werden ignoriert.
  Neue Plattform = eine Zeile in `PLATFORMS`.
- `prices.py` liest den ersten Preis mit Währung aus Titel/Beschreibung („ca. 25 €“).
- Budgetfilter blendet nur aus, was sicher zu teuer ist (ohne Preis / £ / $ bleibt sichtbar).
- Diese Links sind **keine Werbung** (wir verdienen nichts) → Hinweis „Link aus deinem Pin“,
  `rel="nofollow"`. Shop-Seiten werden nicht abgerufen (kein Scraping).
- http://localhost:8000/shop.html#wohnen/pins öffnet Welt + Tab direkt; API: `/api/pin-items?department=wohnen&max_price=30`

## „Mehr wie das“ (Pinterest-Stil)

Klick auf ein Produkt im Shop → `produkt.html?id=…` zeigt es groß und darunter ähnliche
Artikel in Spalten wie bei Pinterest. Jede Kachel ist wieder klickbar.

`similar.py` vergibt Punkte: gleiche Welt (Pflicht), gleiche Kategorie (+2),
Überschneidung der Stile (bis +2) und Farben (bis +1,5), gemessen als Jaccard-Ähnlichkeit
(gemeinsame Begriffe ÷ alle Begriffe). Die Gewichte stehen oben in der Datei.
**Phase 2:** `similar_products()` durch einen Bildvergleich (FashionCLIP) ersetzen.

- http://localhost:8000/api/products/prod-001 – Produkt + ähnliche Artikel

## Genauigkeit messen

```bash
python -m backend.evaluate                 # Demo-Testset
python -m backend.evaluate mein_test.json  # eigenes Testset
```

Ein Testset enthält Pins und von Hand ausgewählte passende Produkte (`relevant`).
Gemessen werden **Treffer@1** (erster Vorschlag passt), **Treffer@5** (mind. ein
passender unter den ersten 5), **Ø Platz** des ersten Treffers und wie viele Pins
**kein Signal** liefern (kein bekanntes Wort). Alle Empfehler in `RECOMMENDERS`
(`backend/evaluate.py`) werden mit demselben Testset verglichen – heute „Nur Pin-Text“
gegen „Text + Board + Bildfarbe“, später z.B. eine Bilderkennung.

Zusätzliche Hinweise neben Titel/Beschreibung: der **Board-Name** („Herbst Outfits“),
der **Alt-Text** des Pins und die **Hauptfarbe des Bildes** (`color_from_hex()` in
`matching.py`; fast weiße und graue Töne werden als Hintergrund ignoriert).

**Achtung:** Das Demo-Testset ist erfunden und eher „leicht“ (die Pins enthalten
meist passende Wörter, der Katalog ist klein). Aussagekräftig wird die Messung erst
mit echten Pins und echten Produkten.

## Hoppel 🐰 – das Maskottchen

Ein kleiner Pixel-Hase, der unten über jede Seite läuft (`frontend/bunny.js`, `bunny.css`):

- hoppelt herum, isst Karotten, schläft, tanzt und hoppelt manchmal zur Maus
- merkt sich seine Position über Seitenwechsel hinweg
- stellt beim ersten Besuch der Startseite die Website vor
- freut sich über 👍 (Herz) und reagiert auf 👎
- **Klick:** verrät, welchen Vibe dein Pinterest abgibt – immer positiv
  (`GET /api/vibe`, Vibes und Sprüche in `backend/vibe.py`)
- lässt sich verstecken (🐾 holt ihn zurück); bei „Bewegung reduzieren“ sitzt er still

**Umzeichnen:** Hoppel ist ein 16×16-Raster aus Buchstaben in `bunny.js` (`IDLE`),
Farben in `PALETTE`. **Ausprobieren** in der Browser-Konsole: `hoppel.tanzen()`,
`hoppel.essen()`, `hoppel.schlafen()`, `hoppel.freuen()`, `hoppel.vibe()`.

## Bilderkennung (FashionCLIP, optional)

Ein KI-Modell wandelt jedes Bild in einen „Fingerabdruck“ (Vektor aus 512 Zahlen) um.
Ähnlich aussehende Kleidung hat ähnliche Vektoren – so versteht die App auch Pins ohne
Text, Schnitte und Muster. Läuft **lokal auf deinem Mac, kostenlos**.

**Einrichten (einmalig):**
```bash
pip install -r requirements-ai.txt     # PyTorch + transformers (groß, dauert etwas)
python -m backend.vision               # lädt beim ersten Mal ~600 MB Modell herunter
```
`python -m backend.vision` berechnet die Vektoren aller Produkt- und Pin-Bilder und
speichert sie in `data/embeddings.json`. **Nach „Pins laden“ oder neuen Produkten erneut
ausführen** – es rechnet nur Neues nach. Die App selbst vergleicht danach nur noch die
gespeicherten Zahlen (das Modell muss nicht laufen).

**Wirkung** (nur wenn `data/embeddings.json` existiert, sonst alles wie bisher):
- Shop: Zusatzpunkte, wenn ein Produkt wie einige deiner Pins **aussieht**
  („Sieht aus wie deine Pins“)
- „Mehr wie das“: Bild-Ähnlichkeit zählt mit, auch ohne gemeinsame Wörter („Sieht ähnlich aus“)
- Messen: `python -m backend.evaluate --bilder` vergleicht zusätzlich „Bilder“ und
  „Text + Bilder“ (braucht ein Testset mit `image_url` – also echte Pins)

**Einstellungen:** Modell per `.env` wählbar (`CLIP_MODEL=…`, Standard
`patrickjohncyh/fashion-clip`; für Wohnen & Deko evtl. `openai/clip-vit-base-patch32`).
Gewichte oben in `vision.py` (`VISUAL_WEIGHT`, `VISUAL_FLOOR`). Vor kommerzieller Nutzung
die **Lizenz des Modells** prüfen.

## 👍 / 👎 Feedback

Auf jeder Produktkachel (Shop und Detailseite) oben rechts. Gespeichert in
`data/feedback.json` (nicht im Git).

- 👎 blendet das Produkt aus (mit „Rückgängig“) und schiebt **ähnliche** Produkte nach unten.
- 👍 schiebt **ähnliche** Produkte nach oben („Ähnlich wie etwas, das dir gefallen hat“).
- „Ähnlich“ kommt aus `similar.py`; wie stark Feedback wirkt, steht oben in `feedback.py`
  (`LIKE_BOOST`, `DISLIKE_PENALTY`).
- Zurücksetzen unter „Mein Pinterest“. API: `GET/POST/DELETE /api/feedback`

## Matching (ohne KI)

1. In Titel + Beschreibung jedes Pins werden Farb- und Stilwörter gesucht (Deutsch + Englisch,
   Synonyme in `COLOR_SYNONYMS` / `STYLE_SYNONYMS` in `backend/matching.py`).
2. Jeder Begriff zählt höchstens einmal pro Pin → Stilprofil, z.B. „beige in 7 von 12 Pins“.
3. Produkte bekommen Punkte für jede passende Farbe/jeden Stil (häufige Begriffe zählen mehr).
   Bei Gleichstand gewinnt das günstigere Produkt.

**Mode vs. Wohnen & Deko:** `CATEGORY_SYNONYMS` ordnet Wörter Kategorien zu („vase“ → Deko,
„hoodie“ → Oberteile). `classify_pin()` entscheidet daraus, ob ein Pin Mode, Wohnen oder
(ohne klares Wort) beides zeigt. Jede Welt hat ihr **eigenes Stilprofil**; Kategorien, die
oft gepinnt werden, geben einen Bonus. Ein `*` vor einem Wort erlaubt deutsche
Zusammensetzungen („*vase“ → „Keramikvase“) – aber nur, wo das nichts Falsches findet
(„*tisch“ fände „praktisch“, „*decke“ fände „Entdecke“).

- http://localhost:8000/api/profile – deine Stilprofile (Mode und Wohnen)
- http://localhost:8000/api/recommendations?department=wohnen&max_price=40 – Empfehlungen mit Begründung

**Ohne Pinterest-Login testen:** `python -m backend.demo_pins` schreibt 19 Beispiel-Pins (Mode + Wohnen)
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
