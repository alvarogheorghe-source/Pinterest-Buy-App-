# Ideen – Malipin als Shop, in den man regelmäßig geht

Stand: 31.10.2026. Neue Richtung: Malipin soll kein Werkzeug sein, das man einmal benutzt, sondern
ein Shop, in den man immer wieder schaut – so wie auf Vinted. Später als echte App.

Noch nichts davon ist gebaut. Reihenfolge = Vorschlag.

## Stufe 1 – Ein Shop zum Stöbern

| Idee | Warum |
|------|-------|
| **Shop zeigt allen sofort Produkte** – auch ohne Foto und ohne Pinterest (heute: leere Einladung) | Ohne Ware kein Stöbern. Der Katalog hat über 20.000 Teile |
| **„Neu heute“** – was in der Nacht dazugekommen ist, ganz oben | Der wichtigste Grund, täglich reinzuschauen |
| **Suchleiste** („schwarze baggy jeans“) | So shoppen die Leute auf Vinted und Zalando |
| **Filter**: Kategorie, Preis, Farbe, Damen/Herren, Marke, Second Hand | Ohne Filter ist ein großer Katalog nicht benutzbar |
| **„Reduziert“** – Teile, deren Preis gesenkt wurde (Feeds liefern den alten Preis) | Schnäppchen ziehen, passt zum Budget-Versprechen |
| **Startseite verkauft den Shop**: „Jeden Tag neue Teile in deinem Stil, im Budget“ – Foto-Suche und Pinterest als Extras | Erwartung richtig setzen |

## Stufe 2 – Der Shop lernt dich kennen

| Idee | Warum |
|------|-------|
| **„Für dich“-Feed** – lernt aus Herzen, Merkliste und Foto-Suchen, ohne Konto und ohne Pinterest | Je öfter man kommt, desto besser wird es – das bindet |
| **Merkliste mit Preisalarm** – „3 gemerkte Teile sind günstiger geworden“ | Echter Grund, jeden Tag nachzuschauen |
| **Malis Fund des Tages** | Kleines tägliches Ritual |
| **Zuletzt angesehen** | Man findet schnell zurück |

## Stufe 3 – Erinnern und App

| Idee | Warum |
|------|-------|
| **Web-App für den Startbildschirm (PWA)** – eigenes Icon, Vollbild | Gratis, schnell; zeigt, ob Leute wiederkommen |
| **Push-Nachrichten** (nur mit Zustimmung): Preis gesunken, neu in deinem Stil | Holt Leute zurück, ohne Werbung zu kaufen |
| **Echte App** im App Store und bei Google Play (Capacitor, gleicher Code) – sobald Pinterest zustimmt und die Web-App gut läuft | Sichtbarkeit im Store, Kamera, Vibration, Leiste unten wie bei Vinted |

Gut zu wissen: Apple ca. 99 €/Jahr, Google einmalig ca. 25 €. Der MacBook Air von 2017 ist zu alt
für die aktuellen Apple-Werkzeuge → App in der Cloud bauen (z. B. Codemagic). Apple lehnt Apps ab,
die nur eine Webseite in einer Hülle sind – die App braucht echte App-Funktionen.

## Zusätzliche Ideen (von Claude)

| Idee | Warum | Aufwand |
|------|-------|---------|
| **Meine Größen** – einmal Größen angeben, der Shop zeigt nur Passendes (wenn die Feeds Größen liefern) | Auf Vinted das Erste, was man einstellt; spart Frust | mittel – erst prüfen, welche Feeds Größen haben |
| **Gespeicherte Suchen** mit „12 neue Teile seit gestern“ | Genau der Mechanismus, der Vinted-Nutzer:innen täglich zurückholt | mittel |
| **Marken folgen** – Neues von Lieblingsmarken im Feed | Persönlich, ohne dass man viel tun muss | klein |
| **Outfit aus der Merkliste bauen** – Teile kombinieren, Gesamtpreis, teilen | Mehr Zeit im Shop, gut für TikTok | mittel |
| **Wunschliste teilen** (Link für Freund:innen, z. B. zum Geburtstag) | Neue Besucher:innen über Freund:innen | klein |
| **Wöchentlicher „Edit“ von Mali** – z. B. „Herbst unter 50 €“, aus den Outfit-Seiten | Frischer Inhalt, auch für Social Media | klein |
| **Wiederkehrende Besucher messen** (anonym, ohne Cookie) in der Admin-Statistik | Nur so sieht man, ob die neue Richtung wirkt | klein |
| **Schnelle Bilder** – Produktbilder verkleinert über den eigenen Server ausliefern | Ein Feed muss flüssig scrollen, sonst wirkt keine App gut | mittel |

## Schon fertig (aus der alten Liste)

- Vibe-Karte zum Teilen (`frontend/vibecard.js`)
- Foto hochladen → Mali findet's, mit Ausschneiden einzelner Kleidungsstücke (`backend/photo.py`, `backend/garments.py`)
- Budget-Outfits als eigene Seiten (`/outfits`, `backend/outfit_pages.py`)
- Englisch als zweite Sprache
- Fund aus der Foto-Suche teilen (`frontend/fitcard.js`)
- Second Hand über Vinted und willhaben (`backend/secondhand.py`)

Verworfen: Preisverlauf, Wisch-Modus.

Zurückgestellt: Mali füttern / Belohnungen, Newsletter per E-Mail (braucht Einwilligung und
Double-Opt-in), „Leute mit deinem Stil mochten auch …“ (lohnt sich erst mit mehr Besucher:innen).
