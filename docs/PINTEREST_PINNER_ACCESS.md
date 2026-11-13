# Pinterest: Antrag auf "pinner data access"

Grund: Seit der Freischaltung (Standard access) antwortet die API bei `/v5/boards` mit
403 `PINNER_DATA_ACCESS_DENIED` / code 6410: "Your application must be approved for pinner data
access." Für Apps, die nach dem 14.09.2026 registriert wurden, ist das eine eigene Freigabe.

Antrag stellen über:
https://developer.pinterest.com/docs/key-concepts/using-beta-and-restricted-features/#request-access-to-closed-beta-or-restricted-features

Vorher selbst eintragen: **App ID** (aus dem Developer-Portal) und den **Link zum Demo-Video**
(z. B. YouTube „nicht gelistet“).

---

**Subject:** Request for pinner data access – Malipin (App ID: [YOUR APP ID])

Hello Pinterest Developer team,

My app Malipin (https://malipin.com, App ID: [YOUR APP ID]) was recently approved for Standard
access. When a user connects their account, calls to `GET /v5/boards` return 403 with code 6410
("Your application must be approved for pinner data access"). I would like to request pinner
data access so that users can use the core feature of the app.

**What Malipin does**
Malipin helps people shop the style they already collect on Pinterest. A user signs in with
Pinterest, chooses which of their own boards Malipin may look at, and Malipin recognises the
style of the pins on those boards (colours, cuts, types of pieces). It then suggests matching
fashion from partner shops and second-hand marketplaces, filtered by the user's budget.

**Which data we read and why**
- `user_accounts:read`: to show the user which account is connected.
- `boards:read`: to list the user's own boards so they can choose which ones to use.
- `pins:read`: to read the pins (image, title, description, link) on the boards the user
  selected. This is the basis for their style profile.

We only read the data of the person who authorised the app, and only the boards they select.
We never create, edit or delete anything on Pinterest, and we never read other users' data.

**How we handle the data**
- Pinterest data is used only to make suggestions for the same user. It is never shown to other
  users, never sold or shared, and never used for ad targeting.
- Pinterest content is never used to train any AI model. Style recognition runs on our own
  server in the EU, only for that user's recommendations.
- Data is stored per user on our EU server and transferred only over HTTPS.
- Users can disconnect and delete all their data with one click on the account page. This
  removes tokens, pins and the style profile immediately. Revoking access in Pinterest settings
  also works.

**Monetisation**
Some product links are affiliate links, clearly labelled as advertising. Pins themselves are
never monetised.

**Links**
- Website: https://malipin.com
- Privacy policy: https://malipin.com/privacy.html
- Terms of use: https://malipin.com/terms.html
- Demo video of the full flow: [LINK TO DEMO VIDEO]

Thank you for considering this request. I'm happy to provide anything else you need.

Best regards,
Alvaro Gheorghe
Malipin – https://malipin.com
company.malipin@gmail.com
