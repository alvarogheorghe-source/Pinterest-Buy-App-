// Merkliste: alle mit ♡ gemerkten Produkte (GET /api/saved).

const savedGrid = document.getElementById("saved-grid");
const summary = document.getElementById("saved-summary");
const deptChips = document.getElementById("dept-chips");

let department = "";  // "" = alle, "mode", "wohnen"

// "3 Teile · zusammen 89,70 €" (übersetzt, Preis im Format der Sprache)
// Summe in der Währung der Person (local_price vom Server; "≈", wenn etwas umgerechnet ist)
function summaryText(items) {
  const total = items.reduce((sum, item) => sum + (item.local_price ?? item.price), 0);
  const currency = items[0]?.local_currency ?? items[0]?.currency ?? "EUR";
  const converted = items.some((item) => item.converted);
  return t(items.length === 1 ? "{n} Teil · zusammen {total}" : "{n} Teile · zusammen {total}",
    { n: items.length, total: money({ price: total, currency, converted }) });
}


function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

async function loadSaved() {
  const query = department ? `?department=${department}` : "";
  const items = await fetch(`/api/saved${query}`).then((r) => r.json());
  render(items);
}

function render(items) {
  savedGrid.replaceChildren();
  showEtsyAttribution(items);
  if (items.length === 0) {
    summary.textContent = "";
    const empty = el("div", "empty saved-empty");
    empty.append(
      el("p", "", department ? "In diesem Bereich hast du noch nichts gemerkt."
        : "Noch nichts gemerkt. Tipp aufs ♡ bei einem Teil, das dir gefällt – dann landet es hier."),
      Object.assign(el("a", "button", "Zum Shop"), { href: "/shop.html" }),
    );
    savedGrid.appendChild(empty);
    return;
  }

  // Summe nur für Euro-Preise (alle Katalog-Produkte sind in Euro)
  summary.textContent = summaryText(items);

  for (const item of items) savedGrid.appendChild(card(item));
}

// Kachel wie im Shop – mit ♡ zum Entfernen statt ♡/👎
function card(item) {
  const box = el("article", "card");
  const detailUrl = `/produkt.html?id=${encodeURIComponent(item.id)}`;

  const imageLink = Object.assign(el("a", "card-link"), { href: detailUrl });
  const imageBox = el("div", "card-image");
  const img = Object.assign(document.createElement("img"),
    { src: item.image_url, alt: item.name, loading: "lazy" });
  img.addEventListener("error", () => {
    imageBox.classList.add("fallback");
    img.replaceWith(document.createTextNode(item.name));
  });
  imageBox.appendChild(img);
  imageLink.appendChild(imageBox);

  const body = el("div", "card-body");
  const titleLink = Object.assign(el("a", "card-link"), { href: detailUrl });
  titleLink.appendChild(el("h3", "card-name", item.name));
  const actions = el("div", "card-actions");
  const shopLink = Object.assign(el("a", "button", "Zum Shop"),
    { href: item.affiliate_url, target: "_blank",
      rel: item.sponsored ? "sponsored noopener" : "noopener" });
  // Nur Affiliate-Links sind Werbung
  actions.append(shopLink, item.sponsored
    ? el("span", "ad-label", "Werbung")
    : el("span", "source-label", t("Link zu {shop}", { shop: shopName(item) })));
  body.append(
    el("p", "card-shop", `${item.shop} · ${t(item.category)}`),
    titleLink,
    el("p", "card-price", money(item)),
    el("p", "card-reason", ""),
    actions,
  );

  // ♡ oben rechts: gefüllt = gemerkt. Klick entfernt von der Merkliste.
  const buttons = el("div", "vote-buttons");
  const heart = Object.assign(el("button", "vote-button like active"),
    { innerHTML: HEART });  // HEART kommt aus feedback.js (fester Inhalt)
  heart.setAttribute("aria-label", "Von der Merkliste entfernen");
  heart.addEventListener("click", async () => {
    if (await sendVote(item.id, null)) removeWithUndo(box, item);
  });
  buttons.appendChild(heart);

  box.append(imageLink, body, buttons);
  return box;
}

// Entfernt – mit "Rückgängig"
function removeWithUndo(box, item) {
  const placeholder = el("div", "dismissed");
  const undo = el("button", "button secondary small", "Rückgängig");
  undo.addEventListener("click", async () => {
    if (await sendVote(item.id, "like")) loadSaved();
  });
  placeholder.append(el("p", "", t("„{name}“ entfernt.", { name: item.name })), undo);
  box.replaceWith(placeholder);
  updateSummaryAfterRemove();
}

// Summe neu berechnen, ohne die Seite neu zu laden (Platzhalter bleiben stehen)
async function updateSummaryAfterRemove() {
  const query = department ? `?department=${department}` : "";
  const items = await fetch(`/api/saved${query}`).then((r) => r.json());
  summary.textContent = items.length
    ? summaryText(items)
    : "Alles entfernt.";
}

deptChips.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  for (const c of deptChips.querySelectorAll(".chip")) c.classList.remove("active");
  chip.classList.add("active");
  department = chip.dataset.dept;
  loadSaved();
});

loadSaved();
