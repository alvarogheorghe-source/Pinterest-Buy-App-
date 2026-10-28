// Shop-Seite: Welt (Mode / Wohnen & Deko), Tabs ("Für dich" / "Aus meinen Pins"),
// Stilprofil, Filter und Raster.

const grid = document.getElementById("product-grid");
const rows = document.getElementById("shop-rows");
const looksBox = document.getElementById("looks");
const resultCount = document.getElementById("result-count");
const banner = document.getElementById("profile-banner");
const categorySelect = document.getElementById("category-select");
const categoryFilter = document.getElementById("category-select");
const budgetSelect = document.getElementById("budget-select");
const pinItemsCount = document.getElementById("pin-items-count");
const tabButtons = document.querySelectorAll(".tab");
const deptButtons = document.querySelectorAll(".dept");

const DEPARTMENT_NAMES = { mode: "Mode", wohnen: "Wohnen & Deko" };

// Aktueller Zustand. Welt und Tab stehen auch in der Adresse, z.B. "#wohnen/pins",
// damit Links und der Zurück-Button funktionieren.
// Damen/Herren entscheidet der Server aus den Pins, sortiert wird immer nach Passung
const filters = { department: "mode", tab: "products", maxPrice: "", category: "" };

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

// --- Daten laden ---------------------------------------------------------------------------

let loadCounter = 0;   // nur die neueste Anfrage darf anzeigen (schnelles Filter-Klicken)

async function load() {
  const current = ++loadCounter;
  showSkeletons();
  const common = new URLSearchParams({ department: filters.department });
  if (filters.maxPrice) common.set("max_price", filters.maxPrice);
  const productParams = new URLSearchParams(common);
  if (filters.category) productParams.set("category", filters.category);

  // Beide Abfragen gleichzeitig starten und auf beide warten
  const [recResponse, pinResponse] = await Promise.all([
    fetch(`/api/recommendations?${productParams}`),
    fetch(`/api/pin-items?${common}`),
  ]);
  if (current !== loadCounter) return;   // inzwischen wurde etwas anderes gewählt
  if (!recResponse.ok || !pinResponse.ok) {
    // Genaue Meldung vom Server zeigen (z.B. "eBay-Anmeldung fehlgeschlagen ...")
    const failed = recResponse.ok ? pinResponse : recResponse;
    const detail = await failed.json().then((d) => d.detail).catch(() => null);
    resultCount.textContent = detail || "Daten konnten nicht geladen werden.";
    grid.innerHTML = "";
    return;
  }
  const recommendations = await recResponse.json();
  labelBudget(recommendations.currency);
  const pinItems = await pinResponse.json();
  const profile = recommendations.profile;

  renderBanner(profile);
  pinItemsCount.textContent = pinItems.length ? `(${pinItems.length})` : "";

  if (filters.tab === "pins") {
    rows.replaceChildren();
    looksBox.hidden = true;
    const items = pinItems;
    renderGrid(items.map(pinItemToCard), "Teil", "Teile",
      profile.pin_count > 0
        ? "Keine Pins mit Shop-Link in diesem Bereich gefunden (oder alle über deinem Budget)."
        : "Lade zuerst deine Pins unter „Mein Pinterest“.");
  } else {
    const hasProfile = profile.pin_count > 0;
    const items = recommendations.products;
    loadLooks(current);
    // Themen-Reihen nur in der Standard-Ansicht (ohne Kategorie-Filter, nach Passung sortiert)
    renderRows(!filters.category
      ? themedRows(recommendations.products, profile, recommendations.currency) : [], hasProfile);
    renderGrid(items.map((p) => productToCard(p, hasProfile)), "Produkt", "Produkte",
      filters.maxPrice || filters.category
        ? "Keine Produkte in diesem Budget. Probier einen höheren Betrag."
        : "");
    // Gar nichts in dieser Welt (noch kein passender Partner-Shop) – ehrlich sagen statt "Budget"
    document.body.classList.toggle("needs-input-mode", Boolean(recommendations.needs_input));
    if (recommendations.needs_input) {
      renderNeedsInput();                // weder Pins noch Foto: Einladung statt Zufallsware
    } else if (!items.length && !filters.maxPrice && !filters.category) {
      renderNoShopsYet(pinItems.length, recommendations.unfitting > 0, recommendations.pending_photos);
    } else {
      showSources(recommendations.sources || ["demo"]);
    }
  }
  showWarnings(filters.tab === "pins" ? [] : recommendations.warnings || []);
}

// --- Shop the Look: zu einem Outfit-Pin die passenden Teile ---------------------------------

async function loadLooks(current) {
  looksBox.hidden = true;
  if (filters.department !== "mode" || filters.category) return;
  const found = await fetch("/api/looks").then((r) => (r.ok ? r.json() : [])).catch(() => []);
  if (current !== loadCounter || !found.length) return;   // inzwischen anderes gewählt
  renderLooks(found);
}

function renderLooks(found) {
  const title = Object.assign(document.createElement("h2"),
    { className: "shop-row-title", textContent: t("Shop the Look") });
  const hint = Object.assign(document.createElement("p"),
    { className: "muted looks-hint", textContent: t("Outfits aus deinen Pins, Teil für Teil zum Nachshoppen.") });
  const track = Object.assign(document.createElement("div"), { className: "looks-track" });
  for (const look of found) track.appendChild(lookCard(look));
  looksBox.replaceChildren(title, hint, track);
  looksBox.hidden = false;
}

function lookCard(look) {
  const card = Object.assign(document.createElement("article"), { className: "look-card" });
  const photo = Object.assign(document.createElement("img"),
    { className: "look-pin", src: look.pin.image_url, alt: look.pin.title || t("Dein Pin"), loading: "lazy" });
  photo.addEventListener("error", () => photo.remove());
  const list = Object.assign(document.createElement("div"), { className: "look-items" });
  for (const item of look.items) {
    const row = Object.assign(document.createElement("a"),
      { className: "look-item", href: `/produkt.html?id=${encodeURIComponent(item.id)}` });
    const thumb = Object.assign(document.createElement("img"),
      { src: item.image_url, alt: "", loading: "lazy" });
    thumb.addEventListener("error", () => thumb.replaceWith(document.createElement("span")));
    const text = document.createElement("span");
    text.append(
      Object.assign(document.createElement("span"), { className: "look-part", textContent: t(item.category) }),
      Object.assign(document.createElement("span"), { className: "look-name", textContent: item.name }),
      Object.assign(document.createElement("span"), { className: "look-price", textContent: money(item) }),
    );
    row.append(thumb, text);
    list.appendChild(row);
  }
  // Ganzer Look: Summe in der eigenen Währung (+ Kennzeichnung, falls Partnerlinks dabei)
  const total = look.items.reduce((sum, item) => sum + (item.local_price ?? item.price), 0);
  const first = look.items[0];
  const footer = Object.assign(document.createElement("p"), { className: "look-total" });
  footer.textContent = t("Ganzer Look: {price}", { price: money({
    price: total, currency: first.local_currency ?? first.currency,
    converted: look.items.some((item) => item.converted) }) });
  if (look.items.some((item) => item.sponsored)) {
    footer.append(" ", Object.assign(document.createElement("span"), { className: "ad-label", textContent: "Werbung" }));
  }
  list.appendChild(footer);
  card.append(photo, list);
  return card;
}

// --- Themen-Reihen: "Weil du Baggy pinnst", "Gerade reduziert", "Unter 20 €", "Second Hand" --

const ROW_MIN = 4;     // kleinere Reihen lohnen sich nicht
const ROW_MAX = 12;
const CHEAP = 20;      // "Unter 20 €" / "$20" / "£20"

// Deine Merkmale, genaueste zuerst: Details (Bootcut, Light Wash …), dann Stile, dann Farben
function favouriteTerms(profile) {
  const details = Object.values(profile.details || {}).flatMap((d) => Object.entries(d));
  details.sort((a, b) => b[1] - a[1]);
  return [...details.map(([name]) => name), ...profile.top_styles, ...profile.top_colors];
}

function themedRows(products, profile, currency = "EUR") {
  const list = [];
  const add = (title, items) => {
    if (items.length >= ROW_MIN) list.push({ title, items: items.slice(0, ROW_MAX) });
  };
  // Das erste Merkmal, zu dem es genug passende Teile gibt
  for (const term of profile.pin_count > 0 ? favouriteTerms(profile) : []) {
    const matching = products.filter((p) => (p.matched || []).includes(term));
    if (matching.length >= ROW_MIN) {
      add(t("Weil du {term} pinnst", { term: t(term) }), matching);
      break;
    }
  }
  add(t("Gerade reduziert"), products.filter((p) => sale(p)).sort((a, b) => sale(b).percent - sale(a).percent));
  const cheap = new Intl.NumberFormat(window.LOCALE || "de-AT",
    { style: "currency", currency, maximumFractionDigits: 0 }).format(CHEAP);
  add(t("Unter {price}", { price: cheap }), products.filter((p) => (p.local_price ?? p.price) <= CHEAP));
  add(t("Second-Hand-Funde"), products.filter((p) =>
    /second hand|vintage/i.test(p.shop) || (p.style_tags || []).includes("vintage")));
  return list;
}

function renderRows(list, hasProfile) {
  rows.replaceChildren();
  for (const row of list) {
    const section = Object.assign(document.createElement("section"), { className: "shop-row" });
    const title = Object.assign(document.createElement("h2"), { className: "shop-row-title", textContent: row.title });
    const track = Object.assign(document.createElement("div"), { className: "row-track" });
    for (const product of row.items) track.appendChild(createCard(productToCard(product, hasProfile)));
    section.append(title, track);
    rows.appendChild(section);
  }
  if (list.length) {
    rows.appendChild(Object.assign(document.createElement("h2"),
      { className: "shop-row-title all-title", textContent: t("Alle Vorschläge") }));
  }
}

// Noch kein Stil bekannt: Mali lädt ein, ein Foto hochzuladen (oder bald Pinterest zu verbinden)
function renderNeedsInput() {
  const box = Object.assign(document.createElement("div"), { className: "empty needs-input" });
  const mali = document.querySelector(".logo-pin");
  if (mali) box.append(Object.assign(mali.cloneNode(true), { classList: "needs-input-mali" }));
  box.append(
    Object.assign(document.createElement("p"), { className: "no-shops-title",
      textContent: "Zeig Mali deinen Stil" }),
    Object.assign(document.createElement("p"), { className: "muted",
      textContent: "Lade ein Foto von einem Outfit oder Teil hoch, das dir gefällt. Mali sucht dir dann passende Teile, neu und Second Hand." }),
  );
  const actions = Object.assign(document.createElement("div"), { className: "no-shops-actions" });
  actions.append(Object.assign(document.createElement("a"),
    { className: "button", href: "/foto.html", textContent: t("Foto hochladen") }), connectButton());
  box.appendChild(actions);
  grid.replaceChildren(box);
  rows.replaceChildren();
  looksBox.hidden = true;
  resultCount.textContent = "";
}

function renderNoShopsYet(pinCount, onlyUnfitting = false, pendingPhotos = 0) {
  const box = Object.assign(document.createElement("div"), { className: "empty no-shops" });
  // onlyUnfitting: Es gibt Produkte, aber keins passt zu deinen Pins -> lieber nichts zeigen
  box.append(
    Object.assign(document.createElement("p"), { className: "no-shops-title",
      textContent: onlyUnfitting
        ? "Noch nichts, was wirklich zu deinen Pins passt."
        : filters.department === "wohnen"
          ? "Für Wohnen & Deko sind gerade noch keine Shops verbunden."
          : "Für Mode sind gerade noch keine Shops verbunden." }),
    Object.assign(document.createElement("p"), { className: "muted",
      textContent: pendingPhotos
        ? t("Mali schaut sich gerade {n} neue Teile genauer an. Lade die Seite in ein paar Minuten neu.", { n: pendingPhotos })
        : "Wir holen laufend neue Partner-Shops dazu. Schau bald wieder vorbei!" }),
  );
  const actions = Object.assign(document.createElement("div"), { className: "no-shops-actions" });
  if (pinCount) {     // Teile aus den eigenen Pins gibt es trotzdem
    const pins = Object.assign(document.createElement("button"), { className: "button",
      textContent: t("Teile aus deinen Pins ansehen ({n})", { n: pinCount }) });
    pins.addEventListener("click", () => writeHash(filters.department, "pins"));
    actions.append(pins);
  }
  const other = filters.department === "wohnen" ? "mode" : "wohnen";
  const switchWorld = Object.assign(document.createElement("button"), { className: "button secondary",
    textContent: other === "mode" ? "Zur Mode" : "Zu Wohnen & Deko" });
  switchWorld.addEventListener("click", () => writeHash(other, "products"));
  actions.append(switchWorld);
  box.append(actions);
  grid.replaceChildren(box);
  resultCount.textContent = "";
}

// Budget in der Währung der Person: "bis 15 €", "up to $15", "up to £15" …
function labelBudget(currency = "EUR") {
  const format = new Intl.NumberFormat(window.LOCALE || "de-AT",
    { style: "currency", currency, maximumFractionDigits: 0 });
  for (const option of budgetSelect.options) {
    if (option.value) option.textContent = t("bis {price}", { price: format.format(option.value) });
  }
}

// --- Woher kommen die Produkte? (Hinweis + Fußzeile) --------------------------------------

const SOURCE_NAMES = { ebay: "eBay", etsy: "Etsy", aliexpress: "AliExpress", feeds: "Partner-Shops" };

function showSources(sources) {
  const online = sources.filter((s) => SOURCE_NAMES[s]).map((s) => SOURCE_NAMES[s]);
  const text = online.length
    ? t("echte Angebote von {shops} (stündlich aktualisiert)", { shops: online.join(t(" und ")) })
    : "Beispielprodukte (erfunden)";
  resultCount.textContent += ` · ${text}`;
  document.getElementById("source-note").textContent =
    online.length ? t("Produkte: {shops}", { shops: online.join(", ") })
      : "";
  // Pflicht-Hinweis aus den Etsy-API-Bedingungen
  document.getElementById("etsy-attribution").hidden = !sources.includes("etsy");
}

// Fällt eine Quelle aus (z.B. eBay-Keys noch nicht freigeschaltet): sichtbar sagen statt still leer
function showWarnings(warnings) {
  const box = document.getElementById("source-warning");
  box.hidden = !warnings.length;
  box.textContent = warnings.map((w) =>
    t("{source} antwortet gerade nicht, deshalb siehst du nur einen Teil der Angebote.",
      { source: t(SOURCE_NAMES[w.source] || w.source) }) + ` (${w.message})`).join(" ");
}

// --- Oben: Stilprofil der gewählten Welt ---------------------------------------------------

function renderBanner(profile) {
  banner.innerHTML = "";
  banner.classList.remove("style-line");
  const title = document.createElement("h1");
  const text = document.createElement("p");
  banner.append(title, text);
  const worldName = DEPARTMENT_NAMES[filters.department];

  const terms = [...profile.top_colors, ...profile.top_styles];
  if (profile.pin_count > 0 && terms.length === 0) {
    // Pins sind da, aber ohne erkennbare Wörter (z.B. nur "fit 🤍")
    title.textContent = t("Dein Stil · {world}", { world: t(worldName) });
    text.className = "muted";
    text.textContent = t("{n} Pins geladen. Sie haben kaum Text, deshalb sortiere ich vor allem nach Bildern und Farben (falls die Bilderkennung eingerichtet ist).", { n: profile.pin_count });
    return;
  }
  if (profile.pin_count === 0) {
    banner.innerHTML = "";               // die Einladung unten (renderNeedsInput) sagt alles
    return;
  }

  // Eine ruhige Zeile: "Dein Stil  Baggy · Schwarz · Streetwear · Jeans   aus 26 Pins"
  banner.classList.add("style-line");
  title.textContent = "Dein Stil";
  text.className = "style-terms";
  // Stile (goth, streetwear …) verlinken ins Stil-Lexikon, Farben/Teile bleiben Text
  const styles = new Set(profile.top_styles);
  [...terms, ...profile.top_categories].slice(0, 6).forEach((term, i) => {
    if (i) text.append(" · ");
    text.append(styles.has(term)
      ? Object.assign(document.createElement("a"), { href: `/stile.html#stil-${term}`, textContent: t(term) })
      : t(term));
  });
  banner.appendChild(Object.assign(document.createElement("span"), {
    className: "muted style-count", textContent: t("aus {n} Pins", { n: profile.pin_count }) }));
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
    t("Mit Pinterest verbinden");
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

// Endlos-Scrollen: erst BATCH Karten, beim Herunterscrollen automatisch die nächsten.
// So bleibt der Shop auch mit 1.000 Angeboten flott (Bilder laden ohnehin erst bei Sicht).
const BATCH = 24;
let pending = [];
const sentinel = Object.assign(document.createElement("div"), { className: "grid-sentinel" });
const moreObserver = new IntersectionObserver((entries) => {
  if (entries.some((entry) => entry.isIntersecting)) showMore();
}, { rootMargin: "800px" });   // rechtzeitig nachladen, bevor man unten ankommt

function showMore() {
  for (const card of pending.splice(0, BATCH)) grid.appendChild(createCard(card));
  if (pending.length) grid.after(sentinel); else sentinel.remove();
}

function renderGrid(cards, singular, plural, emptyText) {
  grid.innerHTML = "";
  resultCount.textContent = `${cards.length} ${t(cards.length === 1 ? singular : plural)}`;
  if (cards.length === 0) {
    pending = [];
    sentinel.remove();
    const empty = document.createElement("p");
    empty.className = "empty muted";
    empty.textContent = emptyText;
    grid.appendChild(empty);
    return;
  }
  pending = [...cards];
  showMore();
  moreObserver.observe(sentinel);
}

// Platzhalter, solange geladen wird – schimmernde Karten statt einer leeren Seite
function showSkeletons(count = 8) {
  pending = [];
  sentinel.remove();
  grid.replaceChildren(...Array.from({ length: count }, () => {
    const card = Object.assign(document.createElement("div"), { className: "card skeleton" });
    card.setAttribute("aria-hidden", "true");
    card.innerHTML = '<div class="card-image"></div><div class="card-body">'
      + '<span class="bone short"></span><span class="bone"></span><span class="bone price"></span></div>';
    return card;
  }));
}

// Produkt aus dem Katalog -> Daten für eine Kachel (mit "Werbung", da Affiliate-Link)
function productToCard(product, hasProfile) {
  return {
    imageUrl: product.image_url,
    topLine: `${product.shop} · ${t(product.category)}`,
    title: product.name,
    price: money(product),
    sale: sale(product),
    note: hasProfile ? shortReason(product) : "",
    // Klick auf Bild oder Name -> Detailseite mit "Mehr wie das"
    detailUrl: `/produkt.html?id=${encodeURIComponent(product.id)}`,
    // 👍/👎 (nur bei Katalog-Produkten)
    productId: product.id,
    vote: product.vote,
    // Hinweis: Bilderkennung ("sieht aus wie deine Pins") oder 👍 ("ähnlich wie ein Like")
    hint: product.looks_like_pins ? "Sieht aus wie deine Pins"
      : product.feedback_hint ? "Ähnlich wie etwas, das dir gefallen hat"
      : product.trusted ? "Aus einem von uns geprüften Shop" : "",
    badge: product.trusted ? "Geprüfter Shop" : "",
    buttonText: "Zum Shop",
    href: product.affiliate_url,
    // Nur wenn wir am Link verdienen (Affiliate), ist es Werbung – sonst "Link zu eBay"
    // sponsored = bezahlter Link (für Suchmaschinen), noopener = Shop kann unsere Seite nicht steuern
    rel: product.sponsored ? "sponsored noopener" : "noopener",
    label: product.sponsored ? "Werbung" : t("Link zu {shop}", { shop: shopName(product) }),
    labelClass: product.sponsored ? "ad-label" : "source-label",
  };
}

// Pin mit Shop-Link -> Daten für eine Kachel (KEINE Werbung: wir verdienen daran nichts)
function pinItemToCard(item) {
  return {
    imageUrl: item.image_url,
    topLine: `${item.platform} · ${t(item.platform_type)}`,
    title: item.title || "Ohne Titel",
    // "ca.", weil der Preis nur aus dem Pin-Text gelesen wurde
    price: item.price != null ? t("ca. {price}", { price: money(item) })
      : "Preis im Shop",
    note: item.description,
    buttonText: "Zum Angebot",
    href: item.link,
    // nofollow = fremder, nicht von uns geprüfter Link
    rel: item.sponsored ? "sponsored noopener" : "nofollow noopener",
    // Über Skimlinks umgeleitet -> Partnerlink -> "Werbung"
    label: item.sponsored ? "Werbung" : "Aus deinem Pin",
    isPinItem: true,
    labelClass: item.sponsored ? "ad-label" : "source-label",
  };
}

// Kurz statt technisch: "Wie deine Pins: Baggy · Schwarz" bzw. "Sieht aus wie deine Pins"
function shortReason(product) {
  if (product.looks_like_pins) return t("Sieht aus wie deine Pins");
  const terms = (product.matched || []).filter((x) => x !== product.category)  // steht schon oben
    .slice(0, 3).map((x) => t(x));
  return terms.length ? t("{terms} wie in deinen Pins", { terms: terms.join(", ") }) : "";
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

  // Oben: "EBAY · SECOND HAND"  ……  "WERBUNG" (Kennzeichnung rechts, wird nie abgeschnitten)
  const topLine = document.createElement("p");
  topLine.className = "card-shop";
  topLine.append(Object.assign(document.createElement("span"),
    { className: "card-shop-name", textContent: data.topLine }));
  if (data.labelClass !== "source-label" || data.isPinItem) {
    topLine.append(Object.assign(document.createElement("span"),
      { className: `card-tag ${data.labelClass}`, textContent: data.label }));
  }

  const title = document.createElement("h3");
  title.className = "card-name";
  title.textContent = data.title;

  const price = document.createElement("p");
  price.className = "card-price";
  price.textContent = data.price;
  // Sale: alter Preis durchgestrichen + "−30 %" auf dem Bild
  if (data.sale) {
    price.append(" ", Object.assign(document.createElement("s"),
      { className: "price-before", textContent: data.sale.before }));
  }

  // Begründung bzw. Beschreibung (füllt den Platz, damit Buttons unten bündig sind)
  const note = document.createElement("p");
  note.className = "card-reason";
  note.textContent = data.note || "";

  // Kein "Zum Shop"-Knopf pro Kachel (wirkt unruhig) – die ganze Kachel ist der Link.

  body.append(topLine, title, price);
  if (data.hint) body.appendChild(Object.assign(document.createElement("p"),
    { className: "card-hint", textContent: data.hint }));
  body.append(note);

  // Bild und Name sind der Link: Katalog-Produkte -> Detailseite (dort "Zum Shop"),
  // Teile aus Pins -> direkt zum Angebot (neuer Tab)
  const makeLink = () => {
    const a = Object.assign(document.createElement("a"), { className: "card-link" });
    a.href = data.detailUrl || data.href;
    if (!data.detailUrl) Object.assign(a, { target: "_blank", rel: data.rel });
    return a;
  };
  if (data.detailUrl || data.href) {
    const imageLink = makeLink();
    imageLink.appendChild(imageBox);
    const titleLink = makeLink();
    title.replaceWith(titleLink);
    titleLink.appendChild(title);
    card.append(imageLink, body);
  } else {
    card.append(imageBox, body);
  }
  if (data.sale) {
    card.classList.add("on-sale");
    card.appendChild(Object.assign(document.createElement("span"),
      { className: "sale-badge", textContent: `−${data.sale.percent} %` }));
  }
  // Abzeichen oben links auf dem Bild ("Geprüfter Shop")
  if (data.badge) {
    card.classList.add("is-trusted");
    card.appendChild(Object.assign(document.createElement("span"),
      { className: "trusted-badge", textContent: data.badge, title: "Diesen Shop haben wir geprüft" }));
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

budgetSelect.addEventListener("change", () => {
  filters.maxPrice = budgetSelect.value;
  load();
});

categorySelect.addEventListener("change", () => {
  filters.category = categorySelect.value;
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
