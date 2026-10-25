// Shop-Seite (Schritt 6): Stilprofil, Filter und Produktraster.

const grid = document.getElementById("product-grid");
const resultCount = document.getElementById("result-count");
const banner = document.getElementById("profile-banner");
const categorySelect = document.getElementById("category-select");
const sortSelect = document.getElementById("sort-select");
const budgetChips = document.getElementById("budget-chips");

// Aktueller Zustand der Filter
const filters = { maxPrice: "", category: "", sort: "match" };

// Preise schön formatieren, z.B. 34.99 -> "34,99 €"
function formatPrice(price, currency) {
  return new Intl.NumberFormat("de-AT", { style: "currency", currency }).format(price);
}

// Lädt Empfehlungen vom Backend (Filter werden als ?max_price=...&category=... angehängt)
async function loadProducts() {
  const params = new URLSearchParams();
  if (filters.maxPrice) params.set("max_price", filters.maxPrice);
  if (filters.category) params.set("category", filters.category);

  const response = await fetch(`/api/recommendations?${params}`);
  if (!response.ok) {
    resultCount.textContent = "Produkte konnten nicht geladen werden.";
    return;
  }
  const data = await response.json();

  renderBanner(data.profile);

  let items = data.products;
  if (filters.sort === "price") {
    // Kopie sortieren, damit die Original-Reihenfolge (nach Passung) erhalten bleibt
    items = [...items].sort((a, b) => a.price - b.price);
  }
  renderProducts(items, data.profile.pin_count > 0);
}

// Oben: Stilprofil anzeigen – oder zum Verbinden einladen
function renderBanner(profile) {
  banner.innerHTML = "";
  const title = document.createElement("h1");
  const text = document.createElement("p");
  banner.append(title, text);

  const terms = [...profile.top_colors, ...profile.top_styles];
  if (profile.pin_count === 0 || terms.length === 0) {
    title.textContent = "Mode, die zu deinem Pinterest passt";
    text.textContent = "Verbinde dein Pinterest-Konto, dann sortieren wir die Produkte nach deinem Stil. ";
    const link = document.createElement("a");
    link.href = "/konto.html";
    link.textContent = "Jetzt verbinden →";
    text.appendChild(link);
    return;
  }

  title.textContent = "Dein Stil";
  text.className = "muted";
  text.textContent = `Aus ${profile.pin_count} Pins erkannt:`;
  const tags = document.createElement("div");
  tags.className = "tag-list";
  for (const term of terms) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = term;
    tags.appendChild(tag);
  }
  banner.appendChild(tags);
}

function renderProducts(items, hasProfile) {
  grid.innerHTML = "";
  resultCount.textContent = `${items.length} ${items.length === 1 ? "Produkt" : "Produkte"}`;

  if (items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty muted";
    empty.textContent = "Keine Produkte in diesem Budget. Probier einen höheren Betrag.";
    grid.appendChild(empty);
    return;
  }
  for (const product of items) {
    grid.appendChild(renderCard(product, hasProfile));
  }
}

// Eine Produktkachel. Alle Texte über textContent -> kein HTML aus den Daten wird ausgeführt.
function renderCard(product, hasProfile) {
  const card = document.createElement("article");
  card.className = "card";

  // Bild (mit Ersatz, falls es nicht lädt)
  const imageBox = document.createElement("div");
  imageBox.className = "card-image";
  const img = document.createElement("img");
  img.src = product.image_url;
  img.alt = product.name;
  img.loading = "lazy"; // erst laden, wenn die Kachel ins Bild scrollt
  img.addEventListener("error", () => {
    imageBox.classList.add("fallback");
    imageBox.textContent = product.name;
  });
  imageBox.appendChild(img);

  const body = document.createElement("div");
  body.className = "card-body";

  const shop = document.createElement("p");
  shop.className = "card-shop";
  shop.textContent = product.shop;

  const name = document.createElement("h3");
  name.className = "card-name";
  name.textContent = product.name;

  const price = document.createElement("p");
  price.className = "card-price";
  price.textContent = formatPrice(product.price, product.currency);

  body.append(shop, name, price);

  // Begründung nur zeigen, wenn es ein Stilprofil gibt
  if (hasProfile) {
    const reason = document.createElement("p");
    reason.className = "card-reason";
    reason.textContent = product.reason;
    body.appendChild(reason);
  } else {
    const spacer = document.createElement("div");
    spacer.className = "card-reason";
    body.appendChild(spacer);
  }

  // "Zum Shop" + Kennzeichnung "Werbung" (in der EU Pflicht bei Affiliate-Links)
  const actions = document.createElement("div");
  actions.className = "card-actions";
  const link = document.createElement("a");
  link.className = "button";
  link.textContent = "Zum Shop";
  link.href = product.affiliate_url;
  link.target = "_blank"; // neuer Tab
  // sponsored = bezahlter Link (für Suchmaschinen), noopener = Shop kann unsere Seite nicht steuern
  link.rel = "sponsored noopener";
  const adLabel = document.createElement("span");
  adLabel.className = "ad-label";
  adLabel.textContent = "Werbung";
  actions.append(link, adLabel);
  body.appendChild(actions);

  card.append(imageBox, body);
  return card;
}

// --- Filter-Bedienung -----------------------------------------------------------------

budgetChips.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  for (const c of budgetChips.querySelectorAll(".chip")) c.classList.remove("active");
  chip.classList.add("active");
  filters.maxPrice = chip.dataset.max;
  loadProducts();
});

categorySelect.addEventListener("change", () => {
  filters.category = categorySelect.value;
  loadProducts();
});

sortSelect.addEventListener("change", () => {
  filters.sort = sortSelect.value;
  loadProducts();
});

// Kategorien für die Auswahlliste holen
async function loadCategories() {
  const categories = await fetch("/api/categories").then((r) => r.json());
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  }
}

loadCategories();
loadProducts();
