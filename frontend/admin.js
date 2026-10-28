// Admin-Seite: geprüfte Shops eintragen und löschen (backend/shops.py).
// Nur mit ADMIN_PASSWORD in .env – sonst antwortet der Server mit 404.

const loginForm = document.getElementById("login-form");
const panel = document.getElementById("admin-panel");
const logoutButton = document.getElementById("admin-logout");
const form = document.getElementById("shop-form");
const formMessage = document.getElementById("form-message");
const list = document.getElementById("shop-list");
const shopCount = document.getElementById("shop-count");
const sellerLabel = document.getElementById("seller-label");
const sellerHint = document.getElementById("seller-hint");

const PLATFORMS = {
  ebay: { name: "eBay", label: "Verkäufername", placeholder: "z.B. adidas_official",
          hint: "Steht auf jeder eBay-Angebotsseite beim Verkäufer." },
  etsy: { name: "Etsy", label: "Shop-Name", placeholder: "z.B. LinenStudio",
          hint: "Aus der Adresse etsy.com/shop/<Name>." },
  aliexpress: { name: "AliExpress", label: "Store-Nummer", placeholder: "z.B. 1101234567",
                hint: "Aus der Adresse aliexpress.com/store/<Nummer>." },
};

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

// --- Anmelden ----------------------------------------------------------------------------------

async function start() {
  const response = await fetch("/api/admin/shops");
  if (response.status === 404) {
    loginForm.hidden = false;
    loginForm.replaceChildren(el("p", "admin-message",
      "Die Admin-Seite ist abgeschaltet. Trag ADMIN_PASSWORD in .env ein und starte neu."));
    return;
  }
  if (response.status === 401) {
    loginForm.hidden = false;
    return;
  }
  panel.hidden = false;
  logoutButton.hidden = false;
  // Produkt-Feeds (feeds.json) als weitere Plattformen: dort ist der Verkäufer der Händler
  for (const feed of await fetch("/api/admin/feeds").then((r) => r.json())) {
    PLATFORMS[feed.name] = { name: `Feed: ${feed.label}`, label: "Händlername (wie im Feed)",
      placeholder: "z.B. Beispiel Store", hint: "Steht im Shop über dem Produktnamen." };
    form.elements.platform.append(Object.assign(el("option", "", `Feed: ${feed.label}`),
      { value: feed.name }));
  }
  renderList(await response.json());
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = document.getElementById("login-message");
  message.textContent = "Prüfe …";
  const response = await fetch("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: document.getElementById("password").value }),
  });
  if (!response.ok) {
    message.textContent = "Falsches Passwort.";
    return;
  }
  loginForm.hidden = true;
  start();
});

logoutButton.addEventListener("click", async () => {
  await fetch("/api/admin/logout", { method: "POST" });
  location.reload();
});

// --- Formular ----------------------------------------------------------------------------------

function showPlatform() {
  const platform = PLATFORMS[form.elements.platform.value];
  sellerLabel.textContent = platform.label;
  form.elements.seller.placeholder = platform.placeholder;
  sellerHint.textContent = platform.hint;
}

form.elements.platform.addEventListener("change", showPlatform);

form.addEventListener("submit", async (event) => {
  event.preventDefault();   // Checkliste & Pflichtfelder prüft der Browser vorher ("required")
  const f = form.elements;
  const response = await fetch("/api/admin/shops", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform: f.platform.value, seller: f.seller.value.trim(),
                           name: f.name.value.trim(), note: f.note.value.trim() }),
  });
  const result = await response.json();
  if (!response.ok) {
    // FastAPI-Fehler: Text oder Liste von Feld-Fehlern
    const detail = Array.isArray(result.detail) ? result.detail.map((d) => d.msg).join(" · ")
      : result.detail;
    formMessage.textContent = `Nicht gespeichert: ${detail}`;
    return;
  }
  formMessage.textContent = `${result.name} ist jetzt geprüft. Alle Angebote bekommen das Abzeichen.`;
  form.reset();
  showPlatform();
  renderList(await fetch("/api/admin/shops").then((r) => r.json()));
});

// --- Liste ---------------------------------------------------------------------------------------

function renderList(shops) {
  shopCount.textContent = `(${shops.length})`;
  list.replaceChildren();
  if (!shops.length) list.appendChild(el("p", "muted", "Noch keine Shops. Trag oben den ersten ein."));
  for (const shop of shops.slice().reverse()) {
    const row = el("article", "admin-card shop-row");
    const text = el("div");
    text.append(
      el("p", "card-shop", `${PLATFORMS[shop.platform]?.name || shop.platform} · ${shop.seller}`),
      el("h3", "card-name", shop.name),
    );
    if (shop.note) text.append(el("p", "muted", shop.note));
    const remove = el("button", "button secondary small", "Löschen");
    row.append(text, remove);
    list.appendChild(row);

    remove.addEventListener("click", async () => {
      if (!confirm(`„${shop.name}“ wirklich aus den geprüften Shops löschen?`)) return;
      await fetch(`/api/admin/shops/${shop.id}`, { method: "DELETE" });
      renderList(await fetch("/api/admin/shops").then((r) => r.json()));
    });
  }
}

showPlatform();
start();
