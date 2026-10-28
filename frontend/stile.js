// Stil-Lexikon (/stile.html): alle Vibes und Stil-Begriffe, erklärt von Mali.
// Daten: /api/styles (backend/style_guide.py). Jeder Eintrag hat eine Adresse
// (#vibe-goth-baddie, #stil-goth) – so verlinken Shop und Mali direkt hierher.

const vibeGrid = document.getElementById("vibe-grid");
const styleList = document.getElementById("style-list");
const vibeIndex = document.getElementById("vibe-index");
const yourVibe = document.getElementById("your-vibe");

const make = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className: className || "", textContent: text || "" });

// Mali groß im Kopf: das Pixel-Logo aus der Kopfzeile, nur größer
function drawMali() {
  const logo = document.querySelector(".logo-pin");
  if (logo) document.getElementById("styles-mali").append(logo.cloneNode(true));
}

function vibeCard(vibe) {
  const card = make("article", `vibe-card look-${vibe.look}`);
  card.id = vibe.slug;
  const head = make("header", "vibe-card-head");
  head.append(make("span", "vibe-emoji", vibe.emoji || "✨"), make("h3", "vibe-title", vibe.title));
  card.append(head);

  if (vibe.mali) {
    const quote = make("blockquote", "vibe-mali");
    quote.append(make("span", "vibe-mali-label", t("Mali sagt")), make("span", "", vibe.mali));
    card.append(quote);
  }
  card.append(make("p", "vibe-about", vibe.about));

  card.append(make("h4", "vibe-sub", t("Typische Teile")));
  const pieces = make("ul", "vibe-pieces");
  for (const piece of vibe.pieces) pieces.append(make("li", "", piece));
  card.append(pieces);

  const foot = make("div", "vibe-foot");
  if (vibe.colors.length) {
    const swatches = make("div", "vibe-swatches");
    swatches.setAttribute("aria-hidden", "true");
    for (const hex of vibe.colors) swatches.append(Object.assign(make("span", "swatch"), { style: `background:${hex}` }));
    foot.append(swatches);
  }
  const tags = make("div", "vibe-tags");
  for (const style of vibe.styles) {
    tags.append(Object.assign(make("a", "vibe-tag", `#${style.name}`), { href: `#${style.slug}` }));
  }
  foot.append(tags);
  card.append(foot);
  return card;
}

function styleItem(style) {
  const item = make("div", "style-item");
  item.id = style.slug;
  item.append(make("h3", "style-name", style.name), make("p", "style-about", style.about));
  if (style.vibes.length) {
    const line = make("p", "style-vibes");
    line.append(`${t("Gehört zu")}: `);
    style.vibes.forEach((vibe, i) => {
      if (i) line.append(" · ");
      line.append(Object.assign(make("a", "", vibe.title), { href: `#${vibe.slug}` }));
    });
    item.append(line);
  }
  return item;
}

// "Dein Vibe laut Mali" – nur, wenn Pins geladen sind
async function showYourVibe(vibes) {
  let vibe;
  try { vibe = await fetch("/api/vibe").then((r) => r.json()); } catch { return; }
  if (!vibe.pin_count || !vibe.slug) return;
  const entry = vibes.find((v) => v.slug === vibe.slug);
  if (!entry) return;
  yourVibe.replaceChildren(
    make("p", "your-vibe-kicker", t("Dein Vibe laut Mali")),
    make("p", "your-vibe-title", `${vibe.emoji ? `${vibe.emoji} ` : ""}${vibe.title}`),
    make("p", "your-vibe-text", vibe.text),
    Object.assign(make("a", "button", t("Mehr dazu")), { href: `#${vibe.slug}` }),
  );
  yourVibe.hidden = false;
}

async function load() {
  drawMali();
  const data = await fetch("/api/styles").then((r) => r.json());
  for (const vibe of data.vibes) {
    vibeGrid.append(vibeCard(vibe));
    vibeIndex.append(Object.assign(make("a", "vibe-chip", `${vibe.emoji || "✨"} ${vibe.title}`),
      { href: `#${vibe.slug}` }));
  }
  for (const style of data.styles) styleList.append(styleItem(style));
  // Mit Adresse aufgerufen (z.B. aus dem Shop: #stil-goth)? Inhalt ist erst jetzt da ->
  // hinscrollen und hervorheben (:target greift bei nachträglich eingefügten Einträgen nicht)
  highlight();
  showYourVibe(data.vibes);
}

function highlight() {
  document.querySelectorAll(".is-target").forEach((el) => el.classList.remove("is-target"));
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (!target) return;
  target.classList.add("is-target");
  target.scrollIntoView({ block: "center", behavior: "smooth" });
}

window.addEventListener("hashchange", highlight);
load();
