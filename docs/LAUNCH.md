# Malipin öffentlich machen: Was es braucht

*Stand: Oktober 2026. Rechtliche und steuerliche Punkte sind eine Orientierung, keine
Rechtsberatung. Zahlen und Bedingungen von Anbietern ändern sich und müssen vor jeder
Entscheidung aktuell geprüft werden.*

## Kurzfazit

**Die Idee ist umsetzbar und kann günstig starten (unter 20 € im Monat).** Die Technik ist
nicht das Hauptproblem, sie ist zu großen Teilen schon gebaut. Die drei echten Hürden sind:

1. **Pinterest-Freigabe:** Für fremde Nutzer braucht die App einen höheren API-Zugang, den
   Pinterest prüft. Das ist das größte Risiko, weil die ganze Idee davon abhängt.
2. **Echte Partnershops:** Affiliate-Netzwerke nehmen meist nur Websites auf, die schon
   online sind und Inhalte haben.
3. **Nutzer finden:** Geld kommt nur über Käufe. Ohne viele aktive Nutzer bleibt der Ertrag klein.

Die Reihenfolge unten ist so gewählt, dass möglichst lange **nichts kostet** und jedes
Risiko möglichst früh geprüft wird.

---

## 1. Pinterest: das größte Risiko

| Was | Warum |
|---|---|
| Trial Access → **Standard Access** beantragen | Mit Trial Access darf die App nur von dir selbst genutzt werden. Für die Öffentlichkeit braucht es eine Prüfung durch Pinterest. Erfahrungsgemäß wollen sie dafür eine laufende App und oft ein Demo-Video sehen. |
| **Developer Guidelines** von Pinterest genau lesen | Dort steht, was man mit Pinterest-Daten tun darf (z.B. Speicherdauer, Anzeige von Pins, Werbung). Eine Shopping-App, die Geld mit Pinterest-Daten verdient, wird genau angeschaut. |
| Pins mit Herkunft anzeigen | Pin-Bilder gehören ihren Erstellern. Im Tab „Aus meinen Pins“ sollte jede Kachel zum Original-Pin bzw. zur Quelle führen. |
| Daten nur so lange speichern wie nötig | Datenschutz und Pinterest-Regeln. Pins z.B. regelmäßig neu laden statt ewig aufheben. |

**Plan B, falls Pinterest ablehnt:** Ein Einstieg ohne Pinterest, z.B. ein kurzes Stil-Quiz
oder das Hochladen eigener Lieblingsbilder (mit der KI aus Phase 2). Das macht die App
unabhängiger. Es lohnt sich, das früh mitzudenken.

---

## 2. Konten: Entscheidung nötig

Die App ist im Moment für **einen** Nutzer gebaut (deine Tokens liegen in `data/tokens.json`).
Für die Öffentlichkeit braucht jeder Nutzer ein eigenes Konto. Zwei Wege:

| | **A: Login mit Pinterest** (Empfehlung für den Start) | **B: E-Mail + Login-Link** |
|---|---|---|
| Wie | Das Pinterest-Konto *ist* das Konto. Wer verbunden ist, ist angemeldet. | Nutzer gibt E-Mail ein und bekommt einen Login-Link (kein Passwort). Pinterest wird danach verbunden. |
| Vorteile | Kein Passwort, das du schützen musst. Am wenigsten Daten. Passt zur Startseite. Schnell gebaut. | Funktioniert auch ohne Pinterest (Plan B). Du kannst Nutzer per E-Mail erreichen (nur mit Einwilligung). |
| Nachteile | Ohne Pinterest-Freigabe gibt es gar kein Konto. | Braucht einen E-Mail-Versanddienst (oft gratis bis zu einer Menge). Mehr Daten, mehr Datenschutz-Pflichten. |

Eigene Passwörter zu speichern rate ich ab: Das ist für Anfänger das größte Sicherheitsrisiko.

**Empfehlung:** Mit A starten, B später ergänzen, falls Plan B nötig wird.

---

## 3. Technik für viele Nutzer

| Aufgabe | Details | Kosten |
|---|---|---|
| Mehrere Nutzer | Datenbank statt JSON-Dateien (SQLite reicht für den Anfang, später PostgreSQL), Tokens pro Nutzer **verschlüsselt** speichern | gratis |
| Sitzungen und Sicherheit | Login-Sitzungen, Schutz gegen gefälschte Anfragen (CSRF), Begrenzung der Anfragen pro Nutzer (Rate Limit), nur HTTPS | gratis |
| Hosting | Ein kleiner Server, am besten in der EU (Datenschutz), z.B. ein kleiner VPS oder ein Dienst wie Render oder Fly.io | ca. 5–10 €/Monat |
| Domain | z.B. `malipin.com` (Name vorher auf Verfügbarkeit und Markenrechte prüfen) | ca. 10–20 €/Jahr |
| HTTPS-Zertifikat | Let's Encrypt | gratis |
| Pinterest-Redirect | Muss auf die echte Adresse zeigen (`https://…/auth/callback`) | gratis |
| Produkt-Feeds | Täglicher automatischer Import der Partner-Feeds über eine neue `ProductSource` | gratis |
| Pins aktualisieren | Hintergrundaufgabe, die Pins und Tokens regelmäßig erneuert | gratis |
| Backups und Fehler-Logs | Tägliches Backup der Datenbank, Fehlermeldungen sammeln | meist gratis |
| KI aus Phase 2 (FashionCLIP) | Produktbilder einmal vorab berechnen, Pins bei Bedarf. Bei wenigen Nutzern reicht derselbe kleine Server, eventuell etwas mehr Arbeitsspeicher. | ca. 0–15 €/Monat zusätzlich |

**Laufende Kosten am Anfang: grob 7–20 € im Monat.**

---

## 4. Recht in Österreich und der EU

| Pflicht | Was zu tun ist | Kosten |
|---|---|---|
| **Impressum** | Pflicht für Websites mit Einnahmen (E-Commerce-Gesetz, Mediengesetz). Name, Anschrift, Kontakt, ggf. Gewerbe. | gratis (Vorlagen z.B. bei der WKO) |
| **Datenschutzerklärung** | Die aktuelle `PRIVACY.md` ist für den Prototyp. Für die Öffentlichkeit: Hosting, Konten, Affiliate-Tracking, Rechtsgrundlagen und Speicherdauern ergänzen. | gratis bis wenige hundert € (Prüfung durch Fachleute) |
| **DSGVO-Pflichten** | Verzeichnis der Verarbeitungen, Vertrag zur Auftragsverarbeitung mit dem Hoster, Konto- und Datenlöschung auf Knopfdruck, Datenauskunft. In Österreich dürfen Jugendliche ab 14 selbst einwilligen. | gratis |
| **Cookies** | Nur technisch nötige Cookies (Login) brauchen keinen Banner. Bei Analyse-Tools oder Tracking: Einwilligung nötig, oder ein Analyse-Tool ohne Cookies wählen. | gratis |
| **Werbekennzeichnung** | ✅ schon umgesetzt („Werbung“ bei Affiliate-Links, „Link aus deinem Pin“ bei fremden Links) | – |
| **Nutzungsbedingungen** | Was die App tut, was nicht, Haftung für Preise und Verfügbarkeit in fremden Shops | gratis bis wenige hundert € |
| **Gewerbe und Steuern** | Sobald Geld fließt: beim **Gründerservice der WKO** fragen (kostenlose Beratung), ob ein Gewerbe nötig ist und welches. Einkommen muss versteuert werden. Für kleine Umsätze gibt es die Kleinunternehmerregelung bei der Umsatzsteuer (Grenze vorher aktuell prüfen). | Beratung gratis |
| **Name und Logo** | Vor dem Start prüfen, ob „Malipin“ oder der gewählte Name als Marke geschützt ist, und keine Logos von Pinterest oder Shops ohne Erlaubnis verwenden | gratis (Markenrecherche online) |

---

## 5. Geld verdienen: Affiliate

| Schritt | Details |
|---|---|
| Netzwerke | Große Modeshops laufen meist über Affiliate-Netzwerke wie **Awin** oder **Tradedoubler**. Auch eBay und Etsy haben Partnerprogramme. Für Depop und Vinted ist mir kein öffentliches Partnerprogramm bekannt. Diese Links bleiben also ohne Provision. |
| Voraussetzung | Meist eine fertige, öffentliche Website mit Impressum und Datenschutzerklärung. Deshalb kommt dieser Schritt **nach** dem Online-Gang. |
| Produktdaten | Die Netzwerke liefern Produkt-Feeds (CSV/XML) mit Bildern, Preisen und Links. Dafür ist `ProductSource` in `backend/products.py` vorbereitet. |
| Provision | In der Mode oft im einstelligen Prozentbereich pro Kauf, je nach Shop unterschiedlich. |

**Beispielrechnung (nur zur Orientierung):**
1.000 aktive Nutzer × 5 Klicks im Monat × 2 % kaufen × 3,50 € Provision ≈ **350 € im Monat**.
Bei 100 Nutzern sind es eher ~35 €. Die Kosten sind niedrig, also ist ein Plus früh
möglich. Für ein echtes Einkommen braucht es aber viele Nutzer.

---

## 6. Nutzer finden

- **Pinterest selbst:** Eigene Pins mit Outfit-Ideen, die auf die App verlinken (passt perfekt zur Zielgruppe)
- **TikTok und Instagram:** „Ich habe mein Pinterest-Board für unter 50 € nachgekauft“-Videos
- **Freunde und Uni:** Eine kleine Beta-Gruppe für ehrliches Feedback, bevor die Werbung startet
- **Second-Hand-Verkäufer:** Wer auf Depop oder Vinted verkauft und auf Pinterest wirbt, hat Interesse, dass die App seine Pins zeigt

---

## 7. Fahrplan

| Phase | Was | Kosten |
|---|---|---|
| ✅ 1 | Prototyp: Pinterest-Login, Pins, Matching, Shop, Tab „Aus meinen Pins“, Startseite | 0 € |
| 1.5 | **Echter Test** mit deinem Pinterest-Konto, sobald Trial Access freigegeben ist. Synonym-Listen an echte Pins anpassen. | 0 € |
| 2 | **Konten** (Entscheidung A oder B), Datenbank, Sicherheit. Optional: FashionCLIP lokal testen. | 0 € |
| 3 | **Online gehen** für eine kleine Testgruppe: Hosting, Domain, HTTPS, Impressum, Datenschutzerklärung, Nutzungsbedingungen | ~10–20 €/Monat + Domain |
| 4 | **Pinterest Standard Access** beantragen (mit laufender App) und parallel **Affiliate-Netzwerke** bewerben. WKO-Beratung zu Gewerbe und Steuern. | 0 € |
| 5 | Echte Produkt-Feeds einbinden, Beta mit Freunden, Feedback einarbeiten | 0 € |
| 6 | Öffentlicher Start und Marketing | nach Budget |

**Nächste konkrete Schritte:**
1. Auf die Pinterest-Freigabe warten und dann echt testen (Phase 1.5)
2. Die Pinterest Developer Guidelines lesen, besonders zu Shopping, Werbung und Speicherung
3. Entscheiden: Konten über Pinterest-Login (A) oder E-Mail (B)?
