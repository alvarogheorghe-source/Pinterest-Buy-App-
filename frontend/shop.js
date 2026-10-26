// Shop-Seite: Welt (Mode / Wohnen & Deko), Tabs ("Für dich" / "Aus meinen Pins"),
// Stilprofil, Filter und Raster.

const grid = document.getElementById("product-grid");
const resultCount = document.getElementById("result-count");
const banner = document.getElementById("profile-banner");
const categorySelect = document.getElementById("category-select");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-select");
const budgetChips = document.getElementById("budget-chips");
const pinItemsCount = document.getElementById("pin-items-count");
const tabButtons = document.querySelectorAll(".tab");
const deptButtons = document.querySelectorAll(".dept");

const DEPARTMENT_NAMES = { mode: "Mode", wohnen: "Wohnen & Deko" };

// Aktueller Zustand. Welt und Tab stehen auch in der Adresse, z.B. "#wohnen/pins",
// damit Links und der Zurück-Button funktionieren.
const filters = { department: "mode", tab: "products", maxPrice: "", category: "", sort: "match" };

// "#wohnen/pins" -> { department: "wohnen", tab: "pins" }
function readHash() {
  const [dept, tab] = location.hash.slice(1).split("/");
  return {
    department: dept === "wohnen" ? "wohnen" : "mode",
    tab: tab === "pins" || dept === "pins" ? "pins" : "products", // "#pins" = alte Adresse
  };
}

function writeHash(department, tab) {
  location.hash = tab === "pins" ? `${department}/pins` : department;
}

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
  const common = new URLSearchParams({ department: filters.department });
  if (filters.maxPrice) common.set("max_price", filters.maxPrice);
  const productParams = new URLSearchParams(common);
  if (filters.category) productParams.set("category", filters.category);

  // Beide Abfragen gleichzeitig starten und auf beide warten
  const [recResponse, pinResponse] = await Promise.all([
    fetch(`/api/recommendations?${productParams}`),
    fetch(`/api/pin-items?${common}`),
  ]);
  if (!recResponse.ok || !pinResponse.ok) {
    // Genaue Meldung vom Server zeigen (z.B. "eBay-Anmeldung fehlgeschlagen ...")
    const failed = recResponse.ok ? pinResponse : recResponse;
    const detail = await failed.json().then((d) => d.detail).catch(() => null);
    resultCount.textContent = detail || "Daten konnten nicht geladen werden.";
    grid.innerHTML = "";
    return;
  }
  const recommendations = await recResponse.json();
  const pinItems = await pinResponse.json();
  const profile = recommendations.profile;

  renderBanner(profile);
  pinItemsCount.textContent = pinItems.length ? `(${pinItems.length})` : "";

  if (filters.tab === "pins") {
    const items = filters.sort === "price" ? sortByPrice(pinItems) : pinItems;
    renderGrid(items.map(pinItemToCard), "Teil", "Teile",
      profile.pin_count > 0
        ? "Keine Pins mit Shop-Link in diesem Bereich gefunden (oder alle über deinem Budget)."
        : "Lade zuerst deine Pins unter „Mein Pinterest“.");
  } else {
    const hasProfile = profile.pin_count > 0;
    const items = filters.sort === "price"
      ? sortByPrice(recommendations.products)
      : recommendations.products;
    renderGrid(items.map((p) => productToCard(p, hasProfile)), "Produkt", "Produkte",
      "Keine Produkte in diesem Budget. Probier einen höheren Betrag.");
    showSources(recommendations.sources || ["demo"]);
  }
}

// --- Woher kommen die Produkte? (Hinweis + Fußzeile) --------------------------------------

const SOURCE_NAMES = { ebay: "eBay", etsy: "Etsy", aliexpress: "AliExpress" };

function showSources(sources) {
  const online = sources.filter((s) => SOURCE_NAMES[s]).map((s) => SOURCE_NAMES[s]);
  const text = online.length
    ? `echte Angebote von ${online.join(" und ")} (stündlich aktualisiert)`
    : "Beispielprodukte (erfunden)";
  resultCount.textContent += ` · ${text}`;
  document.getElementById("source-note").textContent =
    online.length ? `Produkte: ${online.join(", ")}` : "Prototyp mit erfundenen Beispielprodukten";
  // Pflicht-Hinweis aus den Etsy-API-Bedingungen
  document.getElementById("etsy-attribution").hidden = !sources.includes("etsy");
}

// --- Oben: Stilprofil der gewählten Welt ---------------------------------------------------

function renderBanner(profile) {
  banner.innerHTML = "";
  const title = document.createElement("h1");
  const text = document.createElement("p");
  banner.append(title, text);
  const worldName = DEPARTMENT_NAMES[filters.department];

  const terms = [...profile.top_colors, ...profile.top_styles];
  if (profile.pin_count > 0 && terms.length === 0) {
    // Pins sind da, aber ohne erkennbare Wörter (z.B. nur "fit 🤍")
    title.textContent = `Dein Stil · ${worldName}`;
    text.className = "muted";
    text.textContent = `${profile.pin_count} Pins geladen – sie haben kaum Text. Ich sortiere ` +
      "deshalb vor allem nach Bildern und Farben (falls die Bilderkennung eingerichtet ist).";
    return;
  }
  if (profile.pin_count === 0) {
    title.textContent = filters.department === "wohnen"
      ? "Deko und Möbel, die zu deinem Pinterest passen"
      : "Mode, die zu deinem Pinterest passt";
    text.textContent = "Verbinde dein Pinterest-Konto, dann sortieren wir alles nach deinem Stil.";
    banner.appendChild(connectButton());
    return;
  }

  title.textContent = `Dein Stil · ${worldName}`;
  text.className = "muted";
  text.textContent = `Aus ${profile.pin_count} Pins erkannt:`;
  banner.appendChild(tagList(terms));

  // Welche Arten von Teilen zeigen die Pins? (z.B. "Deko", "Leuchten")
  if (profile.top_categories.length) {
    const label = document.createElement("p");
    label.className = "muted banner-sub";
    label.textContent = "Du pinnst oft:";
    banner.append(label, tagList(profile.top_categories, "tag outline"));
  }
}

// Button "Mit Pinterest verbinden" mit Link-Icon (gleich wie auf der Startseite).
// innerHTML ist hier unbedenklich: der Inhalt ist fester Text, keine Daten von außen.
function connectButton() {
  const button = document.createElement("a");
  button.href = "/konto.html";
  button.className = "button connect banner-button";
  button.innerHTML =
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>' +
    '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>' +
    "Mit Pinterest verbinden";
  return button;
}

function tagList(terms, className = "tag") {
  const list = document.createElement("div");
  list.className = "tag-list";
  for (const term of terms) {
    const tag = document.createElement("span");
    tag.className = className;
    tag.textContent = term;
    list.appendChild(tag);
  }
  return list;
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
    topLine: `${product.shop} · ${product.category}`,
    title: product.name,
    price: formatPrice(product.price, product.currency),
    note: hasProfile ? product.reason : "",
    // Klick auf Bild oder Name -> Detailseite mit "Mehr wie das"
    detailUrl: `/produkt.html?id=${encodeURIComponent(product.id)}`,
    // 👍/👎 (nur bei Katalog-Produkten)
    productId: product.id,
    vote: product.vote,
    // Hinweis: Bilderkennung ("sieht aus wie deine Pins") oder 👍 ("ähnlich wie ein Like")
    hint: product.looks_like_pins ? "Sieht aus wie deine Pins"
      : product.feedback_hint ? "Ähnlich wie etwas, das dir gefallen hat" : "",
    buttonText: "Zum Shop",
    href: product.affiliate_url,
    // Nur wenn wir am Link verdienen (Affiliate), ist es Werbung – sonst "Link zu eBay"
    // sponsored = bezahlter Link (für Suchmaschinen), noopener = Shop kann unsere Seite nicht steuern
    rel: product.sponsored ? "sponsored noopener" : "noopener",
    label: product.sponsored ? "Werbung" : `Link zu ${product.shop.split(" · ")[0]}`,
    labelClass: product.sponsored ? "ad-label" : "source-label",
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

  body.append(topLine, title, price);
  if (data.hint) body.appendChild(Object.assign(document.createElement("p"),
    { className: "card-hint", textContent: data.hint }));
  body.append(note, actions);

  // Bild und Name als Link zur Detailseite (nur bei Katalog-Produkten)
  if (data.detailUrl) {
    const imageLink = document.createElement("a");
    imageLink.className = "card-link";
    imageLink.href = data.detailUrl;
    imageLink.appendChild(imageBox);
    const titleLink = document.createElement("a");
    titleLink.className = "card-link";
    titleLink.href = data.detailUrl;
    title.replaceWith(titleLink);
    titleLink.appendChild(title);
    card.append(imageLink, body);
  } else {
    card.append(imageBox, body);
  }
  // 👍/👎 oben rechts auf dem Bild (feedback.js)
  if (data.productId) card.appendChild(createVoteButtons(data.productId, data.vote, card));
  return card;
}

// --- Bedienung ------------------------------------------------------------------------------

// Zeigt, was in der Adresse steht (beim Laden und bei jeder Änderung der Adresse)
async function applyHash() {
  const { department, tab } = readHash();
  if (department !== filters.department) {
    filters.department = department;
    filters.category = ""; // Kategorien der anderen Welt passen nicht mehr
    await loadCategories();
    categorySelect.value = "";
  }
  filters.tab = tab;

  for (const button of deptButtons) {
    const active = button.dataset.dept === department;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active);
  }
  for (const button of tabButtons) {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active);
  }
  // Pins haben keine Kategorie -> Filter dort ausblenden
  categoryFilter.hidden = tab === "pins";
  load();
}

// Klicks ändern nur die Adresse -> "hashchange" -> applyHash()
for (const button of deptButtons) {
  button.addEventListener("click", () => writeHash(button.dataset.dept, filters.tab));
}
for (const button of tabButtons) {
  button.addEventListener("click", () => writeHash(filters.department, button.dataset.tab));
}
window.addEventListener("hashchange", applyHash);

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

// Kategorien der aktuellen Welt in die Auswahlliste schreiben
async function loadCategories() {
  const categories = await fetch(`/api/categories?department=${filters.department}`)
    .then((r) => r.json());
  categorySelect.length = 1; // alle Optionen außer "Alle Kategorien" entfernen
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  }
}

// Start: Kategorien für "Mode" laden, dann anzeigen, was in der Adresse steht
loadCategories().then(applyHash);

// Mali hat die Pins fertig analysiert (analysis.js) -> Empfehlungen neu laden
window.addEventListener("analysis:done", (event) => {
  if (event.detail.status === "done") load();
});
