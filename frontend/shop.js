// Shop-Seite: Stilprofil, Tabs ("Für dich" / "Aus meinen Pins"), Filter und Raster.

const grid = document.getElementById("product-grid");
const resultCount = document.getElementById("result-count");
const banner = document.getElementById("profile-banner");
const categorySelect = document.getElementById("category-select");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-select");
const budgetChips = document.getElementById("budget-chips");
const pinItemsCount = document.getElementById("pin-items-count");
const tabButtons = document.querySelectorAll(".tab");

// Aktueller Zustand. Der Tab steht auch in der Adresse (#pins), damit Links
// und der Zurück-Button funktionieren.
const filters = {
  tab: location.hash === "#pins" ? "pins" : "products",
  maxPrice: "",
  category: "",
  sort: "match",
};

// Preise schön formatieren, z.B. 34.99 -> "34,99 €"
function formatPrice(price, currency) {
  return new Intl.NumberFormat("de-AT", { style: "currency", currency }).format(price);
}

// Sortiert nach Preis. Teile ohne Preis oder in fremder Währung (£, $) kommen ans
// Ende – £35 ist nicht dasselbe wie 35 € und ohne Wechselkurs nicht vergleichbar.
function sortByPrice(items) {
  const euroPrice = (item) =>
    item.price != null && item.currency === "EUR" ? item.price : Infinity;
  return [...items].sort((a, b) => euroPrice(a) - euroPrice(b));
}

// --- Daten laden ---------------------------------------------------------------------------

async function load() {
  const budget = filters.maxPrice ? `max_price=${filters.maxPrice}` : "";
  const productParams = new URLSearchParams(budget);
  if (filters.category) productParams.set("category", filters.category);

  // Beide Abfragen gleichzeitig starten und auf beide warten
  const [recResponse, pinResponse] = await Promise.all([
    fetch(`/api/recommendations?${productParams}`),
    fetch(`/api/pin-items?${budget}`),
  ]);
  if (!recResponse.ok || !pinResponse.ok) {
    resultCount.textContent = "Daten konnten nicht geladen werden.";
    return;
  }
  const recommendations = await recResponse.json();
  const pinItems = await pinResponse.json();

  renderBanner(recommendations.profile);
  pinItemsCount.textContent = pinItems.length ? `(${pinItems.length})` : "";

  if (filters.tab === "pins") {
    const items = filters.sort === "price" ? sortByPrice(pinItems) : pinItems;
    renderGrid(items.map(pinItemToCard), "Teil", "Teile",
      recommendations.profile.pin_count > 0
        ? "Keine Pins mit Shop-Link gefunden (oder alle über deinem Budget)."
        : "Lade zuerst deine Pins unter „Mein Pinterest“.");
  } else {
    const hasProfile = recommendations.profile.pin_count > 0;
    const items = filters.sort === "price"
      ? sortByPrice(recommendations.products)
      : recommendations.products;
    renderGrid(items.map((p) => productToCard(p, hasProfile)), "Produkt", "Produkte",
      "Keine Produkte in diesem Budget. Probier einen höheren Betrag.");
  }
}

// --- Oben: Stilprofil ---------------------------------------------------------------------

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

// --- Raster und Kacheln -------------------------------------------------------------------

function renderGrid(cards, singular, plural, emptyText) {
  grid.innerHTML = "";
  resultCount.textContent = `${cards.length} ${cards.length === 1 ? singular : plural}`;
  if (cards.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty muted";
    empty.textContent = emptyText;
    grid.appendChild(empty);
    return;
  }
  for (const card of cards) grid.appendChild(createCard(card));
}

// Produkt aus dem Katalog -> Daten für eine Kachel (mit "Werbung", da Affiliate-Link)
function productToCard(product, hasProfile) {
  return {
    imageUrl: product.image_url,
    topLine: product.shop,
    title: product.name,
    price: formatPrice(product.price, product.currency),
    note: hasProfile ? product.reason : "",
    buttonText: "Zum Shop",
    href: product.affiliate_url,
    // sponsored = bezahlter Link (für Suchmaschinen), noopener = Shop kann unsere Seite nicht steuern
    rel: "sponsored noopener",
    label: "Werbung",
    labelClass: "ad-label",
  };
}

// Pin mit Shop-Link -> Daten für eine Kachel (KEINE Werbung: wir verdienen daran nichts)
function pinItemToCard(item) {
  return {
    imageUrl: item.image_url,
    topLine: `${item.platform} · ${item.platform_type}`,
    title: item.title || "Ohne Titel",
    // "ca.", weil der Preis nur aus dem Pin-Text gelesen wurde
    price: item.price != null ? `ca. ${formatPrice(item.price, item.currency)}` : "Preis im Shop",
    note: item.description,
    buttonText: "Zum Angebot",
    href: item.link,
    // nofollow = fremder, nicht von uns geprüfter Link
    rel: "nofollow noopener",
    label: "Link aus deinem Pin",
    labelClass: "source-label",
  };
}

// Baut EINE Kachel. Alle Texte über textContent -> kein HTML aus den Daten wird ausgeführt.
function createCard(data) {
  const card = document.createElement("article");
  card.className = "card";

  // Bild – mit Ersatz, falls es fehlt oder nicht lädt
  const imageBox = document.createElement("div");
  imageBox.className = "card-image";
  const showFallback = () => {
    imageBox.classList.add("fallback");
    imageBox.textContent = data.title;
  };
  if (data.imageUrl) {
    const img = document.createElement("img");
    img.src = data.imageUrl;
    img.alt = data.title;
    img.loading = "lazy"; // erst laden, wenn die Kachel ins Bild scrollt
    img.addEventListener("error", showFallback);
    imageBox.appendChild(img);
  } else {
    showFallback();
  }

  const body = document.createElement("div");
  body.className = "card-body";

  const topLine = document.createElement("p");
  topLine.className = "card-shop";
  topLine.textContent = data.topLine;

  const title = document.createElement("h3");
  title.className = "card-name";
  title.textContent = data.title;

  const price = document.createElement("p");
  price.className = "card-price";
  price.textContent = data.price;

  // Begründung bzw. Beschreibung (füllt den Platz, damit Buttons unten bündig sind)
  const note = document.createElement("p");
  note.className = "card-reason";
  note.textContent = data.note || "";

  const actions = document.createElement("div");
  actions.className = "card-actions";
  const link = document.createElement("a");
  link.className = "button";
  link.textContent = data.buttonText;
  link.href = data.href;
  link.target = "_blank"; // neuer Tab
  link.rel = data.rel;
  const label = document.createElement("span");
  label.className = data.labelClass;
  label.textContent = data.label;
  actions.append(link, label);

  body.append(topLine, title, price, note, actions);
  card.append(imageBox, body);
  return card;
}

// --- Bedienung ------------------------------------------------------------------------------

function showTab(tab) {
  filters.tab = tab;
  for (const button of tabButtons) {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active);
  }
  // Pins haben keine Kategorie -> Filter dort ausblenden
  categoryFilter.hidden = tab === "pins";
  load();
}

for (const button of tabButtons) {
  button.addEventListener("click", () => {
    // Adresse ändern -> löst "hashchange" aus -> showTab()
    location.hash = button.dataset.tab === "pins" ? "pins" : "";
  });
}

window.addEventListener("hashchange", () => {
  showTab(location.hash === "#pins" ? "pins" : "products");
});

budgetChips.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  for (const c of budgetChips.querySelectorAll(".chip")) c.classList.remove("active");
  chip.classList.add("active");
  filters.maxPrice = chip.dataset.max;
  load();
});

categorySelect.addEventListener("change", () => {
  filters.category = categorySelect.value;
  load();
});

sortSelect.addEventListener("change", () => {
  filters.sort = sortSelect.value;
  load();
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
showTab(filters.tab);
