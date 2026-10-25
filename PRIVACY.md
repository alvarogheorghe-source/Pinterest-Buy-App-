# Privacy Policy – Style App (Prototype)

*Last updated: 25 October 2026*

Style App is a prototype that connects to a user's Pinterest account, derives a personal
style profile from selected boards and suggests matching clothing and home items. It is
currently used only for development and testing by its author. Later it may earn
commissions through affiliate links (always marked as advertising).

## Who is responsible

This app is developed by the GitHub user
[alvarogheorghe-source](https://github.com/alvarogheorghe-source).
For questions or requests, please open an issue at
https://github.com/alvarogheorghe-source/Pinterest-Buy-App-/issues.

## What data the app accesses

The app uses the official Pinterest API v5 with **read-only** permissions
(`user_accounts:read`, `boards:read`, `pins:read`). After you log in and approve
access on Pinterest, the app can read:

- your Pinterest username
- your boards (name, description, number of pins, cover image)
- pins of the boards you select (image URL, title, description)

The app **never** sees or stores your Pinterest password or cookies. It does not
create, change or delete anything in your Pinterest account.

## Why the data is used

The data is used only to create a style profile (e.g. colors and style keywords) and
to show product suggestions that match it. It is not used for advertising profiles,
not sold, and not shared with third parties – except for the short search terms
described in the next section.

## Product search with eBay and Etsy

To find real products, the app sends short search terms to the official APIs of eBay
and Etsy, for example "beige oversized sweater". These terms only contain a color, a
style word and a product type derived from your pins. They contain **no** username,
no pin images, no pin texts and no other personal data. The search results are stored
on the app's computer for up to one hour.

## Where the data is stored

The app runs locally on the computer of the person using it. Access tokens, the board
selection and pin data are stored as files on that computer only. There is no central
server and no database operated by the developer.

## How long data is kept and how to delete it

- Click **"Verbindung trennen" (disconnect)** in the app to delete the stored access tokens.
- Deleting the app's `data` folder removes all stored data.
- You can revoke the app's access at any time in your Pinterest settings
  (Settings → Security and logins / Apps).

## Links to shops

The app links to products on eBay, Etsy and other shops. Affiliate links (where we
may earn a commission) are marked as advertising ("Werbung"); other links are marked
"Link zu …". When you click a link, you leave the app, and the privacy policy of the
respective shop applies.

## Your rights

Under the EU General Data Protection Regulation (GDPR) you have the right to access,
correct and delete your data, to restrict processing and to complain to a data
protection authority (in Austria: the Datenschutzbehörde, https://www.dsb.gv.at).

## Changes

This policy may be updated as the prototype develops. The current version is always
available at this address.

---

### Kurzfassung auf Deutsch

Die Style App ist ein privater Prototyp. Sie liest über die offizielle Pinterest-API
(nur Lese-Rechte) deinen Benutzernamen, deine Boards und die Pins ausgewählter Boards,
um daraus dein Stilprofil zu erstellen und passende Kleidung und Wohnsachen
vorzuschlagen. Passwörter und Cookies werden nie gespeichert. Alle Daten bleiben lokal
auf dem Computer, auf dem die App läuft. Für die Produktsuche gehen nur kurze
Suchbegriffe wie „beige oversized Pullover“ an eBay und Etsy – ohne Benutzername, Bilder
oder sonstige persönliche Daten. Mit „Verbindung trennen“ werden die
Tokens gelöscht; den Zugriff kannst du jederzeit in deinen Pinterest-Einstellungen
widerrufen.
