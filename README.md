# Malipin (Prototyp)

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
  vibe.py       Malis Vibe-Check („Goth Baddie“, „Clean Girl 🤍“, „Quiet Luxury 💸“ …)
eval/           demo_testset.json: Beispiel-Pins mit von Hand gewählten passenden Produkten
scripts/        make_placeholders.py: erzeugt die Produkt-Platzhalterbilder (frontend/img/products)
  demo_pins.py  schreibt Beispiel-Pins, um ohne Pinterest-Login zu testen
  rss_import.py TESTWERKZEUG: echte Pins eines öffentlichen Boards per RSS laden
  products.py   Produktmodell, austauschbare Produktquelle, Preis-/Kategoriefilter
  storage.py    speichert Daten als JSON in data/
frontend/
  index.html + landing.css  Startseite: stellt die App vor, „Kostenlos starten“
  shop.html + shop.js     Shop: Stilprofil, Tabs, Filter, Produktraster
  produkt.html + produkt.js  Detailseite mit „Mehr wie das“ (ähnliche Artikel)
  feedback.js             ♡/👎-Buttons (Shop und Detailseite)
  merkliste.html + merkliste.js  Merkliste: alle gemerkten Teile mit Summe
  nav.js                  Zähler „♡ Merkliste“ in der Kopfzeile
  bunny.js + bunny.css    Mali, das Pixel-Maskottchen (auf allen Seiten)
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

**Am einfachsten (Mac):** Im Finder `start.command` im Projektordner **doppelklicken**.
Es beendet einen alten Server, startet die App und öffnet sie im Browser.
Das Terminal-Fenster offen lassen, solange du die App benutzt.

**Schon mit Pinterest verbunden?** Dann leitet `localhost:8000` direkt in den Shop weiter.
Die Startseite bleibt unter `localhost:8000/index.html` erreichbar.

Oder von Hand im Terminal:

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

### Echte Produkte von eBay (kostenlos)

Sobald `EBAY_CLIENT_ID` und `EBAY_CLIENT_SECRET` in `.env` stehen, zeigt der Shop **echte
eBay-Angebote** (neu und Second Hand) statt der Beispielprodukte (`backend/ebay.py`):

1. Aus deinem Stilprofil werden Suchbegriffe, z.B. „beige oversized Pullover“ (4 pro Welt).
   Farbe und Stil kommen aus den Pins mit genau dieser Kategorie: weiße Sneaker-Pins →
   „weiß streetwear Sneaker“, auch wenn sonst Beige dominiert.
2. Die offizielle eBay Browse API sucht damit (nur Sofort-Kaufen, auf dem eBay-Marktplatz des
   Landes der Person – siehe „Länder & Währungen“).
3. Aussortiert werden: unter 5 €, Kinder-/Puppen-/Tiersachen, Sammelpakete, Defektes,
   Ersatzteile. Fotos werden in größerer Auflösung geladen (bessere Bilderkennung).
4. Farben, Stile und Kategorie liest die App aus dem Titel – Ranking, ♡/👎 und Bilderkennung
   funktionieren wie vorher.
5. Ergebnisse werden 1 Stunde in `data/ebay_cache.json` gespeichert (gitignored); neue Pins
   leeren den Speicher. So bleibt man weit unter dem Gratis-Limit von eBay.

**Schlüssel holen:** https://developer.ebay.com → kostenloses Konto → „Application Keys“ →
beim **Production**-Keyset: *App ID (Client ID)* → `EBAY_CLIENT_ID`, *Cert ID (Client Secret)*
→ `EBAY_CLIENT_SECRET`.

**Werbung oder nicht?** Ohne Partnerprogramm verdienst du nichts, die Links heißen
„Link zu eBay“. Mit dem eBay Partner Network (https://partnernetwork.ebay.com) trägst du die
Kampagnen-ID als `EBAY_EPN_CAMPAIGN_ID` ein – eBay liefert dann Partnerlinks und die App
markiert sie als „Werbung“.

### Echte Produkte von Etsy (kostenlos, nach Freigabe)

Sobald `ETSY_API_KEY` (Keystring) und `ETSY_SHARED_SECRET` in `.env` stehen, kommen
Etsy-Angebote dazu – Vintage, Handgemachtes, Deko (`backend/etsy.py`). Etsy wird auf
**Englisch** durchsucht („beige oversized sweater“), weil die meisten Titel englisch sind.
Digitale Dateien (Schnittmuster, Druckvorlagen), Bastelmaterial, Nicht-Euro-Preise und
Kinder-/Tiersachen werden aussortiert. Schlüssel: https://www.etsy.com/developers →
„Your Apps“ (Etsy muss die App erst freigeben).

Etsy verlangt einen Hinweis, dass die App nicht von Etsy ist – er erscheint automatisch
in der Fußzeile, sobald Etsy-Produkte angezeigt werden.

### AliExpress – „Der Look – ohne Fake“ (nach Freigabe)

Mit `ALIEXPRESS_APP_KEY`, `ALIEXPRESS_APP_SECRET` und `ALIEXPRESS_TRACKING_ID` in `.env`
(Partnerprogramm portals.aliexpress.com + App auf openservice.aliexpress.com) kommen
AliExpress-Angebote dazu (`backend/aliexpress.py`) – **nur markenlose Teile**:
`backend/counterfeit.py` wirft Angebote mit Markennamen (brands.py + bekannte Luxus-/Sportmarken)
oder Fake-Wörtern („replica“, „1:1“ …) raus, und es wird nie nach Marken gesucht. Partnerlinks
→ immer „Werbung“. Gegen die echte API noch nicht getestet (Zugang fehlt).

### Produkt-Feeds (Awin, Tradedoubler, Adcell, Admitad, CJ …)

`backend/feeds.py` liest beliebig viele Produkt-Feeds (CSV oder XML, auch .gz) und macht
daraus normale Malipin-Produkte. **Neuer Shop / neues Netzwerk = ein Eintrag in
`feeds.json`**, kein neuer Code (Vorlage: `feeds.example.json`; `feeds.json` ist gitignored).

- **Presets** für die Spalten: `awin`, `google` (Google-Shopping-Format, bieten viele Netzwerke
  an) und `generic`; eigene Spaltennamen über `"fields"`.
- **Geheime Schlüssel** nur in `.env`, in der Feed-Adresse als `{NAME}` (z.B. `{AWIN_FEED_KEY}`).
- Welt und Kategorie werden aus Feed-Kategorie + Name erkannt; Produkte ohne Mode/Wohnen,
  ohne Bild, unter 3 € oder in anderen Währungen (`"currencies"`) fliegen raus.
  `"counterfeit_filter": true` für Marktplätze mit vielen Fakes.
- Bis zu 5000 Produkte pro Feed, für alle Personen gleich (`data/feed_products.json`),
  einmal am Tag automatisch im Hintergrund neu geladen. Fällt ein Feed aus, bleiben seine
  alten Produkte.
- Händler aus einem Feed lassen sich als **Geprüfter Shop** markieren (Admin-Seite).
- Importieren & prüfen: `python -m backend.feeds`

### Geprüfte Shops

Statt einzelner Teile prüfen wir **ganze Shops/Verkäufer** (`backend/shops.py`, gespeichert in
`data/trusted_shops.json`, für alle gleich). Ein Shop = Plattform + Verkäufer:
eBay-Verkäufername, Etsy-Shop-Name oder AliExpress-Store-Nummer.
**Admin-Seite** `/admin.html` (nirgends verlinkt): nur mit `ADMIN_PASSWORD` in `.env`, sonst
abgeschaltet. Vor dem Speichern muss die Checkliste abgehakt sein (Originalware/offizieller
Store, gute Bewertungen, EU-Versand, Rückgabe, Kontakt/Impressum).
Danach bekommen **alle** Angebote dieses Shops: Abzeichen „Geprüfter Shop“, kleinen Vorrang bei
passendem Stil (`SHOP_BONUS`), Filter „Nur geprüfte Shops“, Notiz auf der Detailseite.
Bei AliExpress dürfen geprüfte offizielle Markenstores auch Markennamen zeigen.

Große Ketten wie Zara haben kein öffentliches Partnerprogramm/API – solche Shops lassen sich
erst über ein Affiliate-Netzwerk (z.B. Awin) als eigene Quelle anbinden.

### Schnitt & Details

`backend/details.py` kennt rund 150 Merkmale pro Kategorie (Deutsch + Englisch):
Schnitt (Bootcut, Wide Leg, Baggy, Cropped …), Bund, Waschung (Light Wash, Washed Black …),
Länge, Ausschnitt, Ärmel, Material, Muster, kleine Details und genaue Teile („Hoodie“,
„Cargohose“, „Chelsea Boots“ – ersetzen das allgemeine Kategorie-Wort).
Das Profil zählt sie pro Kategorie; die Suche nimmt bis zu 2 Merkmale, die in mind. 25 % der
Pins dieser Kategorie vorkommen („Herren Baggy Light Wash Jeans“). Findet eine genaue Suche
unter 5 Treffer, sucht die App zusätzlich breiter („Herren Jeans“). Im Ranking zählen
passende Merkmale im Produkttitel extra; ein widersprechendes (Skinny statt Bootcut) kostet
Punkte. Neue Merkmale einfach in `DETAILS` eintragen.

**Auch im Bild** (`image_tags.image_details`, mit FashionCLIP): Pro erkanntem Teil treten die
Merkmale jeder Gruppe (Typ, Schnitt, Waschung, Länge, Ausschnitt, Material, Muster …)
gegeneinander an – plus „ganz normal“. Nur ein klarer Gewinner (> 60 %) zählt, höchstens 4 pro
Teil. Ergebnis: `pin["image_details"]`, genutzt von Profil, Suche und Foto-Suche.
Ansehen pro Pin: `python -m backend.image_tags`.

### Mehr Angebote & ein schöner Shop

- **10 Suchen pro Welt** (statt 4) mit je **50 Treffern** – persönlich (Teil, Schnitt, Farbe),
  das Lieblingsteil zusätzlich als **Vintage/Second Hand**, dann Trends.
- **Gemeinsamer Such-Speicher** (`backend/search_cache.py`, `data/search_cache.db`): gleiche
  Suchen aller Personen kosten eine Stunde lang nur eine eBay-Anfrage – so bleiben viele
  Suchen pro Person unter eBays Tageslimit.
- **Trends** (`SearchWords.trends`): Besucher ohne Pins sehen sofort gefragte Teile
  („Baggy Jeans“, „Pilz Lampe“ …) statt eines leeren Shops. Bei der Foto-Suche gibt es keine Trends.
- **Sale:** liefert ein Shop den Preis vor der Reduzierung (eBay `marketingPrice`, Awin UVP,
  Google `price` neben `sale_price`, AliExpress), zeigt die Karte „−30 %“ und den alten Preis
  durchgestrichen (ab 5 % Rabatt).
- **Themen-Reihen** oben im Shop zum Durchwischen: „Weil du … pinnst“, „Gerade reduziert“,
  „Unter 20 €“, „Second-Hand-Funde“ – darunter alle Vorschläge.

### Mehrere Quellen

Sind eBay **und** Etsy eingerichtet, mischt der Shop beide (`products.CombinedSource`) –
das Ranking entscheidet, was oben steht. Fällt eine Quelle aus, kommen die anderen
trotzdem. Die Suchbegriffe baut `backend/search_queries.py` (Deutsch für eBay,
Englisch für Etsy). Eine neue Quelle erbt von `products.CachedSource`, schreibt `fetch()`
und wird in `products.online_sources()` eingetragen.

`PRODUCT_SOURCE=demo` in `.env` erzwingt wieder die Beispielprodukte (Tests machen das immer).

**Weitere Affiliate-Feeds einbinden (später):** In `backend/products.py` eine neue Klasse
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

## Mali 🐰 – das Maskottchen

**Vibe-Karte zum Teilen 📸:** In Malis Vibe-Check gibt es „📸 Vibe teilen“. Das erzeugt im
Browser ein Story-Bild (1080 × 1920): Mali sagt dir in einer Sprechblase deinen Vibe – passend
angezogen vor einem passenden Hintergrund (5 Looks: dunkel, erde, clean, street, romantisch;
Zuordnung in `backend/vibe.py` → `LOOKS`) –, dazu Lieblingsfarben und „Finde deinen Vibe →
malipin.com“ (`frontend/vibecard.js`, wird erst beim ersten Tippen geladen). Am Handy öffnet
sich das Teilen-Menü (Instagram, TikTok, WhatsApp …), am Computer wird das Bild gespeichert.
Es wird nichts hochgeladen. Weitere Ideen: `docs/IDEEN.md`.

**Logo:** Mali als Pinnadel (Hasenkopf + rosa Nadelspitze) und „mali*pin*“ mit Pixel-Herzen
als i-Punkten. Mali blinzelt im Logo ab und zu und wackelt mit den Ohren, wenn man darauf
zeigt. Erzeugt wird es aus einem Pixel-Raster in `scripts/make_logo.py` (auch das
Browser-Tab-Symbol `frontend/img/favicon.svg`): Raster ändern → `python scripts/make_logo.py`.

Ein kleiner Pixel-Hase, der unten über jede Seite läuft (`frontend/bunny.js`, `bunny.css`):

- hoppelt herum, isst Karotten, schläft, tanzt und hoppelt manchmal zur Maus
- merkt sich seine Position über Seitenwechsel hinweg
- **Begrüßung nur beim allerersten Besuch** (gemerkt in localStorage): rosa Bildschirm,
  großer Mali hüpft herein und erklärt, wie er hilft (Boards durchschnuppern, passende
  Mode & Deko finden, aufs Budget achten); nach ca. 7 s fliegt er klein an seinen Platz –
  ganz ohne Klick (Antippen überspringt). Zum Wiederholen: `mali.begruessen()`
- freut sich, wenn du etwas merkst (♡), und reagiert auf 👎
- **Klick:** verrät, welchen Vibe dein Pinterest abgibt – immer positiv
  (`GET /api/vibe`, Vibes und Sprüche in `backend/vibe.py`)
- lässt sich verstecken (🐾 holt ihn zurück); bei „Bewegung reduzieren“ sitzt er still

**Umzeichnen:** Mali ist ein 16×16-Raster aus Buchstaben in `bunny.js` (`IDLE`),
Farben in `PALETTE`. **Ausprobieren** in der Browser-Konsole: `mali.tanzen()`,
`mali.essen()`, `mali.schlafen()`, `mali.freuen()`, `mali.vibe()`.

## Bilderkennung (FashionCLIP, optional)

Ein KI-Modell wandelt jedes Bild in einen „Fingerabdruck“ (Vektor aus 512 Zahlen) um.
Ähnlich aussehende Kleidung hat ähnliche Vektoren – so versteht die App auch Pins ohne
Text, Schnitte und Muster. Läuft **lokal auf deinem Mac, kostenlos**.

**Einrichten (einmalig):**
```bash
pip install -r requirements-ai.txt     # PyTorch + transformers (groß, dauert etwas)
python -m backend.vision               # lädt beim ersten Mal ~600 MB Modell herunter
```
**Automatisch:** Nach „Pins laden“ (oder beim nächsten Seitenaufruf nach einem RSS-Import)
startet die App die Analyse selbst im Hintergrund (`backend/analysis.py`): Farben → Modell
laden → Bilder ansehen → Stil, Teile & Marken → Stil-Schwerpunkte. Währenddessen zeigt
`frontend/analysis.js` Mali, der Karotte knabbert, mit dir redet und den Fortschritt zeigt
(verkleinerbar). Stand abfragen: `GET /api/analysis`, starten: `POST /api/analysis`.
Ohne KI-Pakete laufen nur die Farben – die App funktioniert trotzdem.

Von Hand geht es weiterhin:
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
- **Was ist auf dem Bild?** (`backend/image_tags.py`): FashionCLIP vergleicht jedes Pin-Bild
  mit Beschreibungen („goth dark aesthetic fashion“, „a jacket or coat“ …) und hängt die
  passenden Begriffe an den Pin (`image_styles`, `image_categories`). Das Stilprofil zählt sie
  wie Wörter aus dem Text – Vibe-Check und eBay/Etsy-Suche funktionieren so auch bei Pins
  ohne Text. Läuft mit `python -m backend.vision`; Ergebnis ansehen:
  `python -m backend.image_tags`. Schwellen (wie sicher das Modell sein muss) stehen oben
  in der Datei.
- **Vorprüfung:** Zuerst entscheidet das Modell, ob das Bild Mode, Wohnen oder etwas anderes
  zeigt (Bildschirm/Gerät, Text, Essen, Landschaft, Tier, Fahrzeug, Meme). Nur bei Mode/Wohnen
  gibt es Begriffe – und die Kategorie nur aus dieser Welt (ein Outfit vor einem Poster wird
  nicht zu „Wandgestaltung“). Jeder Begriff wird mit 3 Formulierungen beschrieben und gemittelt
  (zuverlässiger). Die Foto-Suche sagt bei z.B. einem Desktop-Screenshot freundlich, dass sie
  kein Outfit sieht, statt Produkte zu zeigen.
- **Genauigkeit messen:** Testbilder in `testbilder/<Kategorie>/` bzw. `testbilder/_kein/`
  legen (Marke optional im Dateinamen: `bild__Adidas Samba.jpg`), dann
  `python -m backend.image_eval` – zeigt pro Bild erkannt vs. erwartet und die Trefferquoten.
  Der Ordner wird nicht hochgeladen.
- **Herren oder Damen?** Bei Mode-Pins erkennt das Modell zusätzlich Herren-/Damenmode
  (`image_gender`), dazu zählen Wörter wie „men's“ oder „Damen“ (`matching.audience`). Zeigt
  das Board klar eine Richtung, sucht die App bei eBay/Etsy z.B. „Herren oversized Hose“, und
  Vibes wie „Clean Girl“ oder „Coquette“ werden bei Herren-Boards nicht vorgeschlagen
  (stattdessen z.B. „Effortless Cool“ oder „Clean Fit“).
- **Marken** (`backend/brands.py`): 22 Sneaker-Modelle und Streetwear-Marken (Air Force 1,
  Samba, New Balance 550, Carhartt, North Face …). Erkannt im Bild (nur sehr sichere Treffer,
  `image_tags.BRAND_MIN`) und im Text („sambas“, „af1“). Jede erkannte Marke bekommt eine
  gezielte Suche (max. 2 pro Welt, häufigste zuerst): Schuh-Modelle direkt („Herren Onitsuka
  Tiger Mexico 66“), Kleidungsmarken mit dem Teil („Herren Carhartt Jacke“, „Ralph Lauren
  Polo“). Neue Marke = eine Zeile in `brands.py`.

**Viele Pins** (gemessen mit simulierten Boards, 160 Produkte):
- Höchstens **500 Pins** über alle Boards, die neuesten zuerst (`pins.MAX_PINS_TOTAL`).
- **Stil-Schwerpunkte:** Beim Analysieren fasst `vision.build_clusters` ähnliche Pins zu
  Gruppen zusammen (≥ 12, ca. eine pro 40 Pins). Ein Produkt wird erst mit den Gruppen und dann
  nur mit den Pins der 2 ähnlichsten Gruppen verglichen. Shop-Aufruf bei 500 Pins: 0,3 s statt
  1,9 s; bei 3000 Pins: 0,9 s statt 10,6 s – bei praktisch gleichem Ergebnis. Ändern sich die
  Pins, rechnet die App automatisch wieder genau, bis `python -m backend.vision` neu lief.
- `data/embeddings.json` (bei vielen Pins mehrere MB) wird nur neu gelesen, wenn sie sich ändert.

**Einstellungen:** Modell per `.env` wählbar (`CLIP_MODEL=…`, Standard
`patrickjohncyh/fashion-clip`; für Wohnen & Deko evtl. `openai/clip-vit-base-patch32`).
Gewichte oben in `vision.py` (`VISUAL_WEIGHT`, `VISUAL_FLOOR`). Vor kommerzieller Nutzung
die **Lizenz des Modells** prüfen.

## 📷 Foto hochladen → Mali findet's

`/foto.html` (Link „📷 Foto“ oben, Hinweis im Shop): Foto auswählen, aufnehmen (Handy),
hineinziehen oder mit ⌘V einfügen – **ohne Pinterest-Login**. Ablauf (`backend/photo.py`):

1. Der Browser verkleinert das Foto auf max. 768 px (JPEG, ohne Ortsdaten) und schickt es an
   `POST /api/photo`. Der Server analysiert es **nur im Arbeitsspeicher – gespeichert wird es nie.**
2. FashionCLIP erkennt Teil, Stil, Herren/Damen und Marke (wie bei Pins), dazu die Hauptfarbe.
3. Gezielte Suche bei eBay/Etsy nur nach dem, was auf dem Foto ist (z.B. „Herren Carhartt
   Jacke“), sonst im Beispielkatalog.
4. Sortiert nach Begriffen, dann vergleicht das Modell die besten 36 Treffer direkt mit dem
   Foto („Sieht aus wie dein Foto“); erkannte Marke gibt einen Bonus.

Gefundene Online-Produkte merkt sich die App (`data/photo_results.json`, max. 200), damit ♡,
Detailseite und „Mehr wie das“ auch für sie funktionieren – das Foto selbst nicht.
Braucht die KI-Pakete (`requirements-ai.txt`), sonst eine freundliche Meldung.

## ♡ Merkliste

Das ♡ auf jeder Produktkachel merkt ein Teil (und schiebt Ähnliches nach oben).
`merkliste.html` zeigt alle gemerkten Teile – zuletzt gemerkte zuerst, filterbar nach
Mode / Wohnen & Deko, mit Summe („4 Teile · zusammen € 184,96“). Entfernen über das ♡,
mit „Rückgängig“. Die Kopfzeile zeigt auf jeder Seite die Anzahl. API: `GET /api/saved`

## ♡ / 👎 Feedback

Auf jeder Produktkachel (Shop und Detailseite) oben rechts. Gespeichert in
`data/feedback.json` (nicht im Git).

- 👎 blendet das Produkt aus (mit „Rückgängig“) und schiebt **ähnliche** Produkte nach unten.
- ♡ merkt das Teil und schiebt **ähnliche** Produkte nach oben („Ähnlich wie etwas, das dir gefallen hat“).
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

**Mit echten Pins testen, solange die API-Freigabe fehlt:** öffentliche Boards haben einen
RSS-Feed. `python -m backend.rss_import benutzer/board` lädt die letzten ~20–25 Pins
(Bild, Titel, Beschreibung) in `data/pins.json`. Nicht offiziell dokumentiert und nicht immer
zuverlässig – nur zum Testen, die echte App nutzt die API. Am besten eigene Boards nehmen.

**Farben aus Pin-Bildern:** Die Pinterest-API liefert zu jedem Pin die Hauptfarbe
(`dominant_color`), RSS nicht. Fehlt sie, rechnet `backend/pin_colors.py` sie aus dem Bild aus
(Bildmitte, ohne weiße/graue Hintergründe; braucht Pillow). Passiert automatisch beim Laden
der Pins; für schon gespeicherte Pins: `python -m backend.pin_colors`.

**Ohne Pinterest-Login testen:** `python -m backend.demo_pins` schreibt 19 Beispiel-Pins (Mode + Wohnen)
nach `data/pins.json`. Echte Pins („Pins laden“) überschreiben sie.

**Phase 2:** `build_style_profile()` durch eine Bilderkennung ersetzen, die dasselbe
`StyleProfile` liefert – `rank_products()` bleibt gleich.

## Website malipin.com (Vorstellungsseite)

`python scripts/build_site.py` baut aus der Startseite eine **statische** Version in `site/`:
Buttons, die den Server brauchen, werden zu „Bald verfügbar“, dazu kommen Datenschutz
(aus `PRIVACY.md`) und Impressum (aus `website/impressum.json`, Vorlage:
`website/impressum.example.json`). **Ohne Impressum wird nichts gebaut.**

Online geht sie automatisch bei jedem Push (`.github/workflows/pages.yml`, GitHub Pages).
Einmalig nötig: GitHub → Settings → Pages → Source „GitHub Actions“ und Custom domain
`malipin.com`. Lokal ansehen: `python -m http.server -d site 8080`.

### Sprachen: Deutsch + Englisch

Die öffentliche Website gibt es zweisprachig: `/` (Deutsch) und `/en/` (Englisch).
Deutsch bleibt die einzige Quelle (`frontend/index.html`); die englischen Texte stehen in
`frontend/i18n/en.json` („deutscher Text“ → „englischer Text“). Der Build (`scripts/i18n.py`)
übersetzt sichtbare Texte, Bild-/Knopf-Beschreibungen und Meta-Texte und **bricht ab, wenn
ein deutscher Text keine Übersetzung hat** – die englische Seite kann also nie halb deutsch
online gehen. Dazu: `hreflang`-Links, Sitemap mit Sprachvarianten, englisches Vorschaubild
(`og-image-en.png`), englische FAQ-Daten, Sprachumschalter oben und unten, und für Besucher
mit nicht-deutschem Browser ein kleiner Hinweis „Switch to English“ (kein Zwangs-Umleiten).
Mali spricht die Sprache der Seite (`bunny.js`).

**Die App** (Shop, Konto, Merkliste, Foto-Suche, Vibe-Check, Mali) ist ebenfalls zweisprachig:
- `frontend/i18n.js` (in jedem `<head>`) wählt die Sprache – gespeicherte Wahl, sonst
  Browsersprache (Deutsch → Deutsch, alles andere → Englisch) – und setzt das Cookie `lang`.
  Auf Englisch übersetzt es **automatisch jeden Text**, der auf der Seite erscheint, auch
  später eingefügte. Nur Sätze mit Zahlen/Namen brauchen im Code `t("… {n} …", { n })`.
- Das Backend (`backend/i18n.py`) übersetzt mit demselben Wörterbuch: Fehlermeldungen,
  Begründungen („Suits you because …“), Vibe-Check samt allen Sprüchen. `tr("… {n} …", n=3)`.
- Schnitt & Details übersetzt es automatisch aus `details.py`.
- Sprachumschalter: oben in der Kopfzeile (am Handy unten im Footer).
- Die Admin-Seite bleibt Deutsch (nur intern).
- `tests/test_app_i18n.py` meldet jeden Text ohne Übersetzung.

### Länder & Währungen

Jede Person bekommt ihr Land (`backend/region.py`): bewusste Wahl im Footer (Cookie `country`),
sonst ein Länder-Header vom Hosting (z.B. Cloudflare `CF-IPCountry`), sonst die Browsersprache
(`en-US` → USA), sonst `DEFAULT_COUNTRY` aus `.env`. Zum Start: AT, DE, CH, GB, IE, US, CA, AU.
- **Preise & Budget** in der eigenen Währung; umgerechnet mit den täglichen Kursen der EZB
  (`backend/currency.py`, Ersatzkurse falls offline). Umgerechnete Preise zeigen „≈“; im Shop
  gilt der Originalpreis.
- **eBay** sucht auf dem Marktplatz des Landes (ebay.at, ebay.com, ebay.co.uk …), in dessen
  Sprache und Währung; der Zwischenspeicher gilt pro Land.
- **AliExpress** liefert ins Land der Person; **Feeds** zeigen nur Produkte für Länder aus
  ihrem `"countries"`-Eintrag.
- Neues Land: eine Zeile in `REGIONS` (region.py).

**Text auf der Startseite geändert?** Neuen Text in `frontend/i18n/en.json` übersetzen – der Test
`tests/test_i18n.py` sagt genau, welcher fehlt.

### SEO (Google & Teilen)

- **Startseite:** Titel/Beschreibung mit Suchbegriffen, Canonical, Open Graph + Twitter-Karte
  (Vorschaubild `img/og-image.png`), Icons für Google/Apple/Android, `site.webmanifest`.
- **Strukturierte Daten** (JSON-LD: Organization, WebSite, WebApplication, FAQPage) – die
  FAQ-Daten werden aus den sichtbaren Fragen erzeugt. Nach Änderungen an Fragen/Texten:
  `python -m scripts.seo` (ein Test meldet, wenn es vergessen wurde).
- **Website-Build** erzeugt `robots.txt` + `sitemap.xml`; die 404-Seite ist `noindex`.
- **App-Server:** persönliche Seiten (Konto, Merkliste, Shop, Produkt, Admin) sind `noindex`;
  die Foto-Suche ist indexierbar. `/api/` und `/auth/` sind in `robots.txt` gesperrt.
- **Bilder neu erzeugen:** `node scripts/make_seo_images.mjs` (braucht Playwright).
- **Google Search Console:** Domain-Property `malipin.com` anlegen, per DNS-TXT-Eintrag
  bestätigen, dann `https://malipin.com/sitemap.xml` einreichen.

## Mehrere Personen (öffentlicher Server)

Alle persönlichen Daten (Pinterest-Zugang, Boards, Pins, Merkliste, Bewertungen, Malis
Analyse, eBay/Etsy-Zwischenspeicher, Foto-Ergebnisse) liegen in `data/malipin.db` (SQLite,
nicht im Repo) – **getrennt pro Person** (`backend/storage.py`). Gemeinsam ist nur
`data/embeddings.json` (Bild-Fingerabdrücke sind für alle gleich).

- **Lokal** (Standard): eine Person „local“ – alles wie bisher, auch die Terminal-Befehle.
- **Öffentlich:** `MULTI_USER=1` in `.env`. Jede Person bekommt beim ersten Besuch eine
  zufällige, anonyme Kennung im signierten Session-Cookie (1 Jahr) – ohne Anmeldung.
- **Wiedererkennen über Pinterest:** Nach dem Pinterest-Login hängt die Kennung am
  Pinterest-Konto (gespeichert nur als Prüfsumme der ID) – dieselben Daten auf jedem Gerät.
  Anonym Gemerktes wird übernommen (Merkliste zusammengeführt). „Verbindung trennen“ gibt dem
  Browser eine neue, leere Kennung (für geteilte Geräte); beim nächsten Login ist alles wieder da.
- **Alle meine Daten löschen:** Button auf „Mein Pinterest“ (`DELETE /api/me`).
- Alte `data/*.json` werden beim ersten Start automatisch übernommen und nach
  `data/alt-vor-datenbank/` verschoben.

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
