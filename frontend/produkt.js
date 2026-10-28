// Detailseite: ein Produkt groß + "Mehr wie das" (ähnliche Artikel, endlos weiterklickbar).
// Aufruf: produkt.html?id=prod-001

const detail = document.getElementById("detail");
const masonry = document.getElementById("masonry");
const backLink = document.getElementById("back-link");


// Kleiner Helfer: Element mit Klasse und Text bauen (Text immer über textContent)
function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

// Bild mit Ersatz, falls es nicht lädt. Ersetzt NUR das Bild (nicht den ganzen
// Kasten), sonst würden z.B. die 👍/👎-Buttons im Kasten mit gelöscht.
function image(url, alt, box) {
  const img = document.createElement("img");
  img.src = url;
  img.alt = alt;
  img.loading = "lazy";
  img.addEventListener("error", () => {
    box.classList.add("fallback");
    img.replaceWith(document.createTextNode(alt));
  });
  return img;
}

// "Zum Shop" + "Werbung" (Affiliate-Link)
function shopButton(product) {
  const actions = el("div", "card-actions");
  const link = el("a", "button", "Zum Shop");
  link.href = product.affiliate_url;
  link.target = "_blank";
  // Nur Affiliate-Links sind Werbung (siehe shop.js)
  link.rel = product.sponsored ? "sponsored noopener" : "noopener";
  actions.append(link, product.sponsored
    ? el("span", "ad-label", "Werbung")
    : el("span", "source-label", t("Link zu {shop}", { shop: shopName(product) })));
  return actions;
}

function renderDetail(product, hasProfile, amazonUrl) {
  document.title = `${product.name} | Malipin`;
  // Zurück in die richtige Welt des Shops
  backLink.href = `/shop.html#${product.department}`;

  const imageBox = el("div", "detail-image");
  imageBox.appendChild(image(product.image_url, product.name, imageBox));
  // 👍/👎 oben rechts auf dem großen Bild. card = null: 👎 blendet hier nichts aus
  // (man ist ja auf der Seite des Produkts), der Button zeigt nur den Zustand.
  imageBox.appendChild(createVoteButtons(product.id, product.vote, null));

  const info = el("div", "detail-info");
  info.append(
    el("p", "card-shop", `${product.shop} · ${product.category}`),
    el("h1", "detail-name", product.name),
    el("p", "detail-price", money(product)),
  );
  if (hasProfile) info.appendChild(el("p", "detail-reason", product.reason));
  if (product.trusted) {
    const box = el("div", "trusted-note");
    box.append(el("strong", "", "Geprüfter Shop, diesen Verkäufer haben wir uns angeschaut"));
    if (product.trusted_note) box.append(el("p", "", product.trusted_note));
    info.appendChild(box);
  }

  const tags = el("div", "tag-list");
  for (const term of [...product.colors, ...product.style_tags]) {
    tags.appendChild(el("span", "tag", term));
  }
  info.append(tags, shopButton(product));
  // Ähnliches bei Amazon suchen (Partnerlink, backend/amazon.py) – nur in AT/DE/CH
  if (amazonUrl) {
    const more = el("p", "amazon-link");
    more.append(Object.assign(el("a", "", "Ähnliches bei Amazon suchen"),
      { href: amazonUrl, target: "_blank", rel: "sponsored noopener" }), el("span", "ad-label", "Werbung"));
    info.append(more);
  }

  detail.replaceChildren(imageBox, info);
}

// Pinterest-Look: Kacheln unterschiedlich hoch. Die Höhe hängt fest an der ID,
// damit dasselbe Produkt immer gleich aussieht.
const RATIOS = ["4 / 5", "1 / 1", "3 / 4", "4 / 5", "2 / 3"];
function ratioFor(id) {
  let sum = 0;
  for (const char of id) sum += char.charCodeAt(0);
  return RATIOS[sum % RATIOS.length];
}

function renderSimilar(items) {
  masonry.replaceChildren();
  if (items.length === 0) {
    masonry.appendChild(el("p", "muted", "Keine ähnlichen Artikel gefunden."));
    return;
  }
  for (const item of items) {
    // Die ganze Kachel ist ein Link -> Klick zeigt wieder "Mehr wie das" für dieses Produkt
    const card = el("a", "pin-card");
    card.href = `/produkt.html?id=${encodeURIComponent(item.id)}`;

    const imageBox = el("div", "pin-card-image");
    imageBox.style.aspectRatio = ratioFor(item.id);
    imageBox.appendChild(image(item.image_url, item.name, imageBox));

    const body = el("div", "pin-card-body");
    body.append(
      el("p", "pin-card-name", item.name),
      el("p", "pin-card-price", money(item)),
    );
    if (item.looks_similar) {
      body.appendChild(el("p", "card-hint", "Sieht ähnlich aus")); // Bilderkennung
    }
    if (item.shared.length) {
      body.appendChild(el("p", "pin-card-shared", t("Auch {terms}", { terms: item.shared.slice(0, 3).map((x) => t(x)).join(" · ") })));
    }
    card.append(imageBox, body);

    // Hülle, damit die 👍/👎-Buttons NICHT im Link liegen (sonst würde ein Klick
    // darauf zur Detailseite springen). Bei 👎 wird die ganze Hülle ersetzt.
    const wrap = el("div", "pin-card-wrap");
    wrap.append(card, createVoteButtons(item.id, item.vote, wrap));
    masonry.appendChild(wrap);
  }
}

async function init() {
  const id = new URLSearchParams(location.search).get("id");
  const response = id ? await fetch(`/api/products/${encodeURIComponent(id)}`) : null;
  if (!response || !response.ok) {
    detail.replaceChildren(el("p", "empty muted", "Dieses Produkt gibt es nicht (mehr)."));
    document.querySelector(".more-like").hidden = true;
    return;
  }
  const data = await response.json();
  renderDetail(data.product, data.has_profile, data.amazon_url);
  renderSimilar(data.similar);
  showEtsyAttribution([data.product, ...data.similar.map((item) => item.product || item)]);
}

init();
