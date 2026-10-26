// Foto hochladen → Mali findet's (POST /api/photo, siehe backend/photo.py)
//
// Das Foto wird im Browser verkleinert (schneller, weniger Daten) und dann geschickt.
// Der Server schaut es nur kurz an und speichert es NICHT.

const drop = document.getElementById("photo-drop");
const input = document.getElementById("photo-input");
const result = document.getElementById("photo-result");
const preview = document.getElementById("photo-preview");
const sprite = document.getElementById("photo-sprite");
const bubble = document.getElementById("photo-bubble");
const foundBox = document.getElementById("photo-found");
const actions = document.getElementById("photo-actions");
const grid = document.getElementById("photo-grid");

const MAX_SIDE = 768;   // reicht der Bilderkennung völlig
const LOOKING = [
  "Ooh, zeig mal her … 👀",
  "Ich schau mir Schnitt, Farbe und Details an …",
  "Ist das eine Marke, die ich kenne? 🤔",
  "Ich such dir jetzt ähnliche Teile – Second Hand inklusive!",
  "Fast geschafft, ich hoppel so schnell ich kann! 🥕",
];
const GENDER = { herren: "Herren", damen: "Damen" };

let talkTimer = null;
let chewTimer = null;

// --- Mali ------------------------------------------------------------------------------------

function drawMali(frameName) {
  const pixels = window.mali && window.mali.pixels;
  if (!pixels) return;
  const frame = pixels.frames[frameName];
  sprite.width = frame[0].length;
  sprite.height = frame.length;
  const ctx = sprite.getContext("2d");
  ctx.clearRect(0, 0, sprite.width, sprite.height);
  frame.forEach((row, y) => row.forEach((cell, x) => {
    if (cell === ".") return;
    ctx.fillStyle = pixels.palette[cell];
    ctx.fillRect(x, y, 1, 1);
  }));
}

function say(text) {
  bubble.textContent = text;
}

function startLooking() {
  let i = 0;
  say(LOOKING[0]);
  talkTimer = setInterval(() => say(LOOKING[++i % LOOKING.length]), 2600);
  let bite = false;
  chewTimer = setInterval(() => drawMali((bite = !bite) ? "eat1" : "eat2"), 420);
}

function stopLooking(frameName) {
  clearInterval(talkTimer);
  clearInterval(chewTimer);
  drawMali(frameName);
}

// --- Foto vorbereiten --------------------------------------------------------------------------

// Verkleinern auf max. 768 px und als JPEG – dabei fallen auch Ortsdaten (EXIF) weg
async function shrink(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
}

// --- Hochladen & Ergebnis ------------------------------------------------------------------------

async function handle(file) {
  if (!file || !file.type.startsWith("image/")) {
    showError("Das ist kein Foto – probier's mit einem JPG, PNG oder Screenshot.");
    return;
  }
  let blob;
  try {
    blob = await shrink(file);
  } catch {
    showError("Dieses Bildformat kann dein Browser nicht öffnen. Probier einen Screenshot davon!");
    return;
  }
  drop.hidden = true;
  result.hidden = false;
  document.body.classList.add("photo-open");   // der kleine Mali unten macht Pause
  grid.replaceChildren();
  foundBox.replaceChildren();
  actions.replaceChildren();
  if (preview.src) URL.revokeObjectURL(preview.src);
  preview.src = URL.createObjectURL(blob);
  startLooking();

  lastBlob = blob;
  await send(blob, false);
}

// Foto an den Server schicken. force: "Da ist doch ein Fit drauf" -> Vorprüfung überspringen
async function send(blob, force) {
  let response, data;
  try {
    response = await fetch(`/api/photo${force ? "?force=true" : ""}`,
      { method: "POST", body: blob, headers: { "Content-Type": "image/jpeg" } });
    data = await response.json();
  } catch {
    stopLooking("idle");
    showError("Ich erreiche den Server gerade nicht. Probier's gleich nochmal!");
    return;
  }
  if (!response.ok) {
    stopLooking("idle");
    showError(data.detail || "Da hat was nicht geklappt.");
    return;
  }
  stopLooking("happy");
  showResult(data);
}

function chip(text) {
  return Object.assign(document.createElement("span"), { className: "chip", textContent: text });
}

// Kein Outfit, nichts fürs Zuhause: was Mali stattdessen sieht (Vorprüfung, image_tags.py)
const NOT_FASHION = {
  desktop: "Hmm, ich seh da eher einen Bildschirm als ein Outfit.",
  device: "Das sieht nach einem Gerät aus – Kleidung oder Deko find ich darauf nicht.",
  text: "Da steht vor allem Text – ich such aber nach Teilen zum Anziehen oder Hinstellen.",
  food: "Sieht lecker aus! Aber anziehen kann man das leider nicht.",
  landscape: "Schöne Aussicht! Nur ein Outfit find ich darauf nicht.",
  animal: "Süß! Ich such aber nach Fits, nicht nach Fell.",
  vehicle: "Schickes Fahrzeug – ich such aber Kleidung und Deko.",
  meme: "Haha! Aber da ist kein Teil drauf, das ich suchen kann.",
  game: "Gutes Game? Ich such aber nur Fits und Deko.",
  sports: "Sportlich! Aber ein Outfit zum Nachshoppen seh ich da nicht.",
};

// Wenn Mali sich nicht sicher ist, WAS drauf ist: neutral bleiben statt falsch raten
const NOT_FASHION_UNSURE = [
  "Hmm, auf dem Bild find ich kein Outfit und nichts fürs Zuhause.",
  "Da seh ich leider kein Teil, das ich suchen könnte.",
  "Ich hab genau hingeschaut – aber kein Fit entdeckt.",
];

function showResult(data) {
  if (data.relevant === false) {
    const unsure = NOT_FASHION_UNSURE[Math.floor(Math.random() * NOT_FASHION_UNSURE.length)];
    say(`${t(NOT_FASHION[data.seen] || unsure)} `
      + t("Probier einen Screenshot von einem Fit oder ein Foto von einem Teil!"));
    drawMali("idle");
    addAgainButton();
    addForceButton();
    return;
  }
  const f = data.found;
  const seen = [...f.categories, ...(f.details || []), ...f.brands, ...f.colors, ...f.styles];
  if (f.gender) seen.push(GENDER[f.gender]);
  if (seen.length) {
    say(t("Ich seh: {terms}! Hier sind ähnliche Teile 🥕", { terms: seen.slice(0, 3).map((x) => t(x)).join(", ") }));
    foundBox.append(Object.assign(document.createElement("p"), { textContent: "Mali sieht:" }));
    for (const term of seen) foundBox.appendChild(chip(term));
  } else {
    say("Hmm, das ist schwer zu erkennen – aber schau mal, was ich gefunden hab!");
  }
  if (!data.products.length) {
    say("Dazu hab ich leider nichts Passendes gefunden. Probier ein anderes Foto!");
  }
  for (const product of data.products) grid.appendChild(card(product));
  addAgainButton();
}

function showError(text) {
  drop.hidden = true;
  result.hidden = false;
  document.body.classList.add("photo-open");
  say(text);
  addAgainButton();
}

let lastBlob = null;

// Mali hat sich geirrt? Dann trotzdem nach Mode suchen lassen
function addForceButton() {
  const force = Object.assign(document.createElement("button"),
    { className: "button secondary", textContent: "Da ist doch ein Fit drauf" });
  force.addEventListener("click", () => {
    actions.replaceChildren();
    say("Okay, ich schau nochmal ganz genau hin!");
    startLooking();
    send(lastBlob, true);
  });
  actions.appendChild(force);
}

function addAgainButton() {
  actions.replaceChildren();
  const again = Object.assign(document.createElement("button"), { className: "button", textContent: "Anderes Foto" });
  again.addEventListener("click", () => {
    document.body.classList.remove("photo-open");
    result.hidden = true;
    drop.hidden = false;
    grid.replaceChildren();
    input.value = "";
    input.click();
  });
  actions.appendChild(again);
}

// --- Produktkarte (wie im Shop) ------------------------------------------------------------------

function formatPrice(price, currency = "EUR") {
  return new Intl.NumberFormat(window.LOCALE || "de-AT", { style: "currency", currency }).format(price);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function card(product) {
  const box = el("article", "card");
  const detailUrl = `/produkt.html?id=${encodeURIComponent(product.id)}`;
  const imageLink = Object.assign(el("a", "card-link"), { href: detailUrl });
  const imageBox = el("div", "card-image");
  const img = Object.assign(document.createElement("img"), { src: product.image_url, alt: product.name, loading: "lazy" });
  img.addEventListener("error", () => { imageBox.classList.add("fallback"); img.replaceWith(product.name); });
  imageBox.appendChild(img);
  imageLink.appendChild(imageBox);

  const body = el("div", "card-body");
  const titleLink = Object.assign(el("a", "card-link"), { href: detailUrl });
  titleLink.appendChild(el("h3", "card-name", product.name));
  const actionsRow = el("div", "card-actions");
  const shop = Object.assign(el("a", "button", "Zum Shop"), {
    href: product.affiliate_url, target: "_blank", rel: product.sponsored ? "sponsored noopener" : "noopener",
  });
  actionsRow.append(shop, product.sponsored
    ? el("span", "ad-label", "Werbung")
    : el("span", "source-label", t("Link zu {shop}", { shop: shopName(product) })));
  body.append(
    el("p", "card-shop", `${product.shop} · ${t(product.category)}`),
    titleLink,
    el("p", "card-price", formatPrice(product.price, product.currency)),
    el("p", "card-reason", product.looks_like_photo ? "Sieht aus wie dein Foto" : product.reason),
    actionsRow,
  );
  box.append(imageLink, body, createVoteButtons(product.id, null, box)); // ♡ / 👎 aus feedback.js
  return box;
}

// --- Foto bekommen: Auswahl, Ziehen, Einfügen ----------------------------------------------------

input.addEventListener("change", () => handle(input.files[0]));
drop.addEventListener("dragover", (event) => { event.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  handle(event.dataTransfer.files[0]);
});
document.addEventListener("paste", (event) => {
  const file = [...event.clipboardData.files].find((f) => f.type.startsWith("image/"));
  if (file) handle(file);
});
