# Malipin auf einen Server bringen

Ziel: **https://malipin.com** zeigt die echte App (Shop, Foto-Suche, Merkliste) statt der
Vorstellungsseite. Pinterest-Login steht für Besucher auf "Bald verfügbar", bis Pinterest
uns den Standard-Zugang gibt. Dauer: ca. 1 Stunde (plus Bilderkennung, läuft allein).

Was du brauchst: ein Konto bei einem Server-Anbieter, Zugriff auf die DNS-Einstellungen
deiner Domain, deine `.env` vom Mac.

---

## 1. Server mieten (Hetzner, ca. 7 €/Monat)

1. https://www.hetzner.com/cloud -> Konto anlegen
2. Neues Projekt -> **Server hinzufügen**
   - Standort: **Falkenstein oder Nürnberg** (Deutschland, gut für Datenschutz)
   - Image: **Ubuntu 24.04**
   - Typ: **CX32** (4 vCPU, 8 GB RAM) – die Bilderkennung braucht den Arbeitsspeicher.
     CX22 (4 GB) geht zur Not auch, ist aber knapp.
   - **SSH-Schlüssel** hinzufügen (sicherer als Passwort). Auf dem Mac:
     ```
     ssh-keygen -t ed25519        # Enter, Enter, Enter
     cat ~/.ssh/id_ed25519.pub    # diese Zeile bei Hetzner einfügen
     ```
3. Nach dem Erstellen steht die **IP-Adresse** des Servers da (z.B. `91.98.12.34`).

## 2. Domain auf den Server zeigen lassen

Bei deinem Domain-Anbieter, DNS-Einstellungen von malipin.com:

| Typ | Name | Wert |
|---|---|---|
| A | `@` | IP des Servers |
| A | `www` | IP des Servers |

Die alten Einträge für GitHub Pages (A-Records `185.199.…` bzw. CNAME auf `github.io`)
**löschen**. Bis die Änderung überall ankommt: 5 Minuten bis einige Stunden.

## 3. Einrichten (ein Befehl)

Auf dem Mac im Terminal:
```
ssh root@DEINE-SERVER-IP
curl -fsSL https://raw.githubusercontent.com/alvarogheorghe-source/Pinterest-Buy-App-/main/deploy/setup.sh -o setup.sh
bash setup.sh
```
Installiert Python, die App, die Bilderkennung, Caddy (HTTPS) und die Firewall.
Dauert ca. 10 Minuten.

## 4. Die `.env` auf den Server kopieren

Auf dem **Mac** (neues Terminal-Fenster, im Projektordner):
```
scp .env root@DEINE-SERVER-IP:/opt/malipin/.env
```
Dann auf dem **Server** anpassen:
```
nano /opt/malipin/.env
```
Diese Zeilen ändern bzw. ergänzen:
```
PINTEREST_REDIRECT_URI=https://malipin.com/auth/callback
PINTEREST_OPEN=0
PUBLIC_URL=https://malipin.com
SESSION_SECRET=<neuer zufälliger Wert, siehe unten>
ADMIN_PASSWORD=<ein langes eigenes Passwort>
```
Zufallswert erzeugen: `python3 -c "import secrets; print(secrets.token_hex(32))"`
Speichern: Ctrl+O, Enter, Ctrl+X. Dann:
```
chown malipin:malipin /opt/malipin/.env && chmod 600 /opt/malipin/.env
systemctl restart malipin
```

**Pinterest:** auf developers.pinterest.com -> deine App -> Redirect-URI
`https://malipin.com/auth/callback` **zusätzlich** eintragen (die localhost-Adresse kann bleiben).
**eBay:** bei der Marketplace-Account-Deletion-Adresse ggf. auch auf malipin.com umstellen.

## 5. Produkte und Bilder zum ersten Mal laden

```
sudo -u malipin bash -c "cd /opt/malipin && .venv/bin/python -m backend.feeds && .venv/bin/python -m backend.vision"
```
Die Bilderkennung dauert beim ersten Mal ca. 30–60 Minuten (Fortschritt wird angezeigt).
Danach läuft beides **jede Nacht um 3:17** von selbst, nur für Neues.

## 6. Prüfen

- https://malipin.com öffnet sich mit Schloss-Symbol (HTTPS)
- Shop zeigt Produkte, Foto-Suche funktioniert
- "Pinterest – bald verfügbar" statt Login-Button
- Impressum und Datenschutz unten verlinkt
- Selbst Pinterest testen: https://malipin.com/admin.html -> mit ADMIN_PASSWORD anmelden,
  dann geht "Mit Pinterest verbinden" für dich

## Später: neue Version einspielen

Nach jedem `git push` vom Mac, auf dem Server:
```
bash /opt/malipin/deploy/update.sh
```

## Wenn etwas nicht geht

| Problem | Befehl |
|---|---|
| Läuft die App? | `systemctl status malipin` |
| Fehlermeldungen der App | `journalctl -u malipin -n 50` |
| HTTPS/Domain-Problem | `journalctl -u caddy -n 50` (meist: DNS zeigt noch nicht auf den Server) |
| Nächtlicher Lauf | `journalctl -u malipin-nightly -n 50` |

## Vor dem Start noch erledigen

- **Datenschutzerklärung** (PRIVACY.md) an den Server anpassen: Hosting bei Hetzner,
  Server-Logs, Bilderkennung, Affiliate-Netzwerke (Awin, eBay, Etsy). Am besten einmal
  von jemandem prüfen lassen.
- GitHub Pages abschalten (Repo -> Settings -> Pages), sobald die Domain auf den Server zeigt.
