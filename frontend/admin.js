// Admin-Seite: Malipin Picks eintragen, bearbeiten, löschen (backend/picks.py).
// Nur mit ADMIN_PASSWORD in .env – sonst antwortet der Server mit 404.

const loginForm = document.getElementById("login-form");
const panel = document.getElementById("admin-panel");
const logoutButton = document.getElementById("admin-logout");
const form = document.getElementById("pick-form");
const formTitle = document.getElementById("form-title");
const formMessage = document.getElementById("form-message");
const cancelEdit = document.getElementById("cancel-edit");
const preview = document.getElementById("image-preview");
const list = document.getElementById("pick-list");
const pickCount = document.getElementById("pick-count");

let categories = { mode: [], wohnen: [] };
let editingId = null;

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

const formatPrice = (price) =>
  new Intl.NumberFormat("de-AT", { style: "currency", currency: "EUR" }).format(price);

// --- Anmelden ----------------------------------------------------------------------------------

async function start() {
  const response = await fetch("/api/admin/picks");
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
  showPanel(await response.json());
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

async function showPanel(picks) {
  categories = await fetch("/api/admin/categories").then((r) => r.json());
  fillCategories();
  panel.hidden = false;
  logoutButton.hidden = false;
  renderList(picks);
}

// --- Formular ----------------------------------------------------------------------------------

function fillCategories(selected) {
  const select = form.elements.category;
  select.replaceChildren(...categories[form.elements.department.value].map((name) =>
    Object.assign(el("option", "", name), { value: name })));
  if (selected) select.value = selected;
}

form.elements.department.addEventListener("change", () => fillCategories());
form.elements.image_url.addEventListener("input", () => {
  const url = form.elements.image_url.value;
  preview.hidden = !url.startsWith("https://");
  if (!preview.hidden) preview.src = url;
});
preview.addEventListener("error", () => { preview.hidden = true; });

function resetForm() {
  editingId = null;
  form.reset();
  fillCategories();
  preview.hidden = true;
  formTitle.textContent = "Neuen Pick eintragen";
  cancelEdit.hidden = true;
}

cancelEdit.addEventListener("click", resetForm);

form.addEventListener("submit", async (event) => {
  event.preventDefault();   // Checkliste & Pflichtfelder prüft der Browser vorher ("required")
  const f = form.elements;
  const data = {
    name: f.name.value.trim(), seller: f.seller.value.trim(), price: Number(f.price.value),
    department: f.department.value, category: f.category.value, url: f.url.value.trim(),
    image_url: f.image_url.value.trim(), note: f.note.value.trim(), sponsored: f.sponsored.checked,
  };
  const response = await fetch(editingId ? `/api/admin/picks/${editingId}` : "/api/admin/picks", {
    method: editingId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) {
    // FastAPI-Fehler: Text oder Liste von Feld-Fehlern
    const detail = Array.isArray(result.detail)
      ? result.detail.map((d) => d.msg.replace("Value error, ", "")).join(" · ")
      : result.detail;
    formMessage.textContent = `Nicht gespeichert: ${detail}`;
    return;
  }
  formMessage.textContent = editingId ? "Gespeichert." : "Pick ist jetzt im Shop.";
  resetForm();
  renderList(await fetch("/api/admin/picks").then((r) => r.json()));
});

// --- Liste ---------------------------------------------------------------------------------------

function renderList(picks) {
  pickCount.textContent = `(${picks.length})`;
  list.replaceChildren();
  if (!picks.length) list.appendChild(el("p", "muted", "Noch keine Picks – trag oben den ersten ein."));
  for (const pick of picks.slice().reverse()) {
    const card = el("article", "card is-pick");
    const imageBox = el("div", "card-image");
    const img = Object.assign(document.createElement("img"),
      { src: pick.image_url, alt: pick.name, loading: "lazy" });
    img.addEventListener("error", () => {   // Foto-Link kaputt -> Name statt kaputtem Bild
      imageBox.classList.add("fallback");
      img.replaceWith("Foto lädt nicht – Link prüfen");
    });
    imageBox.appendChild(img);
    const body = el("div", "card-body");
    const edit = el("button", "button small", "Bearbeiten");
    const remove = el("button", "button secondary small", "Löschen");
    const actions = el("div", "card-actions");
    actions.append(edit, remove);
    body.append(
      el("p", "card-shop", `${pick.shop} · ${pick.category}`),
      el("h3", "card-name", pick.name),
      el("p", "card-price", formatPrice(pick.price)),
      el("p", "card-reason", [...pick.colors, ...pick.style_tags].join(" · ") || "–"),
      actions,
    );
    card.append(imageBox, body);
    list.appendChild(card);

    edit.addEventListener("click", () => startEdit(pick));
    remove.addEventListener("click", async () => {
      if (!confirm(`„${pick.name}“ wirklich aus den Picks löschen?`)) return;
      await fetch(`/api/admin/picks/${pick.id}`, { method: "DELETE" });
      renderList(await fetch("/api/admin/picks").then((r) => r.json()));
    });
  }
}

function startEdit(pick) {
  editingId = pick.id;
  const f = form.elements;
  f.name.value = pick.name;
  f.seller.value = pick.shop.replace(/^Malipin Pick · /, "");
  f.price.value = pick.price;
  f.department.value = pick.department;
  fillCategories(pick.category);
  f.url.value = pick.affiliate_url;
  f.image_url.value = pick.image_url;
  f.note.value = pick.pick_note;
  f.sponsored.checked = pick.sponsored;
  preview.src = pick.image_url;
  preview.hidden = false;
  formTitle.textContent = "Pick bearbeiten";
  cancelEdit.hidden = false;
  formMessage.textContent = "";
  form.scrollIntoView({ behavior: "smooth" });
}

start();
