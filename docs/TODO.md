# Malipin – To-do-Liste (der Reihe nach)

**Du** = Alvaro, **Claude** = Code. Abhaken mit `[x]`.

## 1. Shop fertig machen (vor dem Hosten)

- [x] **Claude:** Stil-Box oben schlanker (eine Zeile: "Dein Stil: Baggy · Schwarz · Streetwear")
- [x] **Claude:** Foto-Suche als kleiner Kamera-Knopf in der Filterzeile statt großem Kasten
- [x] **Claude:** Begründung unter den Karten kürzer ("Wie deine Pins: Sneaker · Weiß")
- [x] **Claude:** Mali-Fenster "Fertig!" verschwindet von selbst
- [x] **Claude:** Footer aufräumen (kein "Prototyp mit Beispielprodukten", kein "Link zu …")
- [ ] **Claude:** Bewertungs-Werkzeug: 30–50 Teile mit "passt / passt nicht" markieren -> Trefferquote messen
- [ ] **Du:** Bewertung durchklicken, **Claude:** Regeln danach nachstellen
- [ ] **Claude:** Datenschutzerklärung anpassen (Server, Cookies, Bilderkennung, Awin/eBay/Etsy),
      "Prototype" raus
- [ ] **Du:** Datenschutz kurz prüfen lassen (z.B. WKO-Beratung)

## 2. Shops anmelden (geht sofort, parallel zu 1.)

- [ ] **Du:** Awin -> "Uniqlo DE" suchen und beitreten
- [ ] **Du:** Awin -> nach "H&M" suchen
- [ ] **Du:** Amazon PartnerNet anmelden (partnernet.amazon.de)
- [x] **Du:** Skimlinks anmelden (skimlinks.com) -> SKIMLINKS_ID in .env eintragen
- [ ] **Du:** Auf zalando.de und aboutyou.de ganz unten nach "Partnerprogramm" schauen
- [ ] **Du:** Bei Direct-Running nachsehen, ob sie nach Österreich liefern -> Claude schaltet EU frei
- [ ] **Du:** Weiter deutsche/österreichische Shops mit Produkt-Feed auf Awin
      (`python -m backend.feeds --kandidaten`)
- [ ] **Du:** AliExpress-Support (Anmeldung wegen "ali" im Namen) – noch offen

## 3. Online gehen (Anleitung: docs/SERVER.md)

- [ ] **Du:** Ist das GitHub-Repo öffentlich oder privat? (privat -> Claude ergänzt Zugangsschlüssel)
- [ ] **Du:** Hetzner-Konto + Server CX32 (Ubuntu 24.04, Deutschland), SSH-Schlüssel
- [ ] **Du:** DNS von malipin.com auf die Server-IP umstellen
- [ ] **Du + Claude:** `setup.sh` auf dem Server ausführen
- [ ] **Du:** `.env` auf den Server kopieren und anpassen (PINTEREST_OPEN=0, PUBLIC_URL …)
- [ ] **Du:** Pinterest-App: Redirect-URI `https://malipin.com/auth/callback` ergänzen
- [ ] **Du:** Feeds + Bilderkennung einmal laufen lassen
- [ ] **Du + Claude:** Alles prüfen (HTTPS, Shop, Foto-Suche, Impressum, Datenschutz)
- [ ] **Du:** GitHub Pages abschalten (Repo -> Settings -> Pages)

## 4. Nach dem Start

- [ ] **Du:** Pinterest Standard-Zugang beantragen (Video der laufenden App)
- [ ] **Du:** Neu bewerben bei Absagen (Snipes, Adcell …) – jetzt mit Live-Seite
- [ ] **Du:** Partnerize, Rakuten Advertising, Impact.com, Tradedoubler, Webgains anmelden
- [ ] **Claude:** Jedes neue Netzwerk einbinden, sobald es zusagt
- [ ] **Claude:** Pinterest für alle freischalten (PINTEREST_OPEN entfernen), sobald genehmigt

## 5. Später / nice to have

- [ ] **Du:** Mac auf natives Python umstellen (Bilderkennung 3–5× schneller)
- [ ] Besucherstatistik ohne Cookie-Banner (z.B. Plausible)
- [ ] Kompakte Handy-Ansicht + "Zum Shop"-Leiste auf der Produktseite

## Erledigt (Auswahl)

- [x] eBay freigeschaltet (Hauptquelle), Etsy + AliExpress nur Wohnen & Deko
- [x] Awin verbunden, Feeds automatisch, `--kandidaten`, `--liste`
- [x] Filter: Unterwäsche/Kinder/Ramsch/Billigware/KI-Bilder/Luxusmarken raus,
      Widersprüche (Skinny statt Baggy) nie, Foto muss passen, Damen/Herren
- [x] Richtige Währung, nur lieferbare Angebote
- [x] Edleres Shop-Design, schlanke Filter
- [x] Server-Konfiguration + Anleitung (docs/SERVER.md)
