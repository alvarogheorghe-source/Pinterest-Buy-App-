# Pinterest Standard Access: Bewerbung

Antworten zum Kopieren in das Formular auf developers.pinterest.com (deine App -> "Upgrade" bzw.
"Request Standard access"). Englisch, weil das Formular englisch ist.

**Vorher erledigen** (sonst lehnt Pinterest ab):
- Malipin läuft online unter https://malipin.com (mit HTTPS)
- Datenschutzerklärung ist aktuell und erreichbar: https://malipin.com/datenschutz.html
- Redirect-URI https://malipin.com/auth/callback ist in der Pinterest-App eingetragen
- Demo-Video ist aufgenommen (Ablauf unten)
- App-Logo: docs/brand/malipin-icon-1024.png (ohne Schrift) oder malipin-logo-1024.png

---

## App name

Malipin

## Website

https://malipin.com

## Short description

Malipin turns your Pinterest boards into a personal shop. It reads the style of the boards you
choose and suggests matching fashion and home decor from partner shops, filtered by your budget.

## What does your app do? (detailed)

Malipin helps people shop the style they already collect on Pinterest. After signing in with
Pinterest, the user picks which of their own boards Malipin should look at. Malipin reads the
pins on those boards and recognises colours, styles, cuts and types of pieces (for example
"black baggy jeans" or "Japandi ceramics"). It then shows matching products from partner shops
and second-hand marketplaces, sorted by how well they fit the user's style and filtered by the
user's budget.

The user always sees why a product was suggested, can save products to a wish list and can hide
products they don't like. A second tab shows items from the user's own pins that already link to
a shop, so they can find them again easily. Each of these links back to the original source.

## How will you use the Pinterest API? Which scopes and why?

We only read data. We never create, edit or delete anything on Pinterest.

- **user_accounts:read** to show the user which Pinterest account is connected.
- **boards:read** to list the user's boards so they can choose which ones Malipin should use.
- **pins:read** to read the pins (image, title, description, link) on the selected boards. This
  is the basis for the style profile and the suggestions.

Pinterest data is only used to make suggestions for the same user who connected their account.
It is never shown to other users, never shared with or sold to third parties and never used to
target ads.

## How do you store and protect Pinterest data?

- Access tokens and pins are stored per user on our server in the EU and are only accessible to
  that user's session. All traffic uses HTTPS.
- To recognise styles, Malipin computes a numeric description of each pin image. This happens on
  our own server, only for that user's recommendations. Pinterest content is not used to train
  any model.
- Pins are refreshed when the user reloads them, instead of being kept indefinitely.
- On the account page the user can disconnect Pinterest and delete all their data with one
  click. This removes the tokens, pins, style profile and wish list immediately.

## How do you make money?

Some product links are affiliate links. When a user buys something through them, the shop pays
us a small commission. These links are clearly labelled as advertising ("Werbung") in the app.
Pins themselves are never monetised, and Pinterest data is not sold or shared.

## Privacy policy

https://malipin.com/datenschutz.html

## Contact

alvaro.gheorghe@schmelz.at

---

## Demo-Video (1–2 Minuten, Bildschirmaufnahme)

Pinterest will sehen, dass alles so funktioniert wie beschrieben. Auf dem Mac: **Cmd+Shift+5**
-> "Bildschirm aufnehmen". Ablauf:

1. malipin.com öffnen, kurz die Startseite zeigen
2. Auf "Mit Pinterest verbinden" klicken, bei Pinterest anmelden und Zugriff erlauben
   (die Pinterest-Seite mit den Berechtigungen gut sichtbar zeigen)
3. Boards auswählen und "Pins laden"
4. Im Shop zeigen: dein Stil oben, passende Produkte, die kurze Begründung unter einem Produkt
5. Ein Produkt öffnen, die Kennzeichnung "Werbung" zeigen
6. Tab "Aus meinen Pins" zeigen
7. Unter "Mein Pinterest" auf "Alle meine Daten löschen" klicken und zeigen, dass die Daten weg sind

Video z.B. als "nicht gelistet" auf YouTube hochladen und den Link ins Formular einfügen.
