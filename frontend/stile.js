// Stil-Lexikon (/stile.html): alle Vibes und Stil-Begriffe, erklärt von Mali.
// Daten: /api/styles (backend/style_guide.py). Jeder Eintrag hat eine Adresse
// (#vibe-goth-baddie, #stil-goth) – so verlinken Shop und Mali direkt hierher.
// Läuft NACH bunny.js: Malis Pixel-Bilder kommen aus window.mali.pixels.

const vibeGrid = document.getElementById("vibe-grid");
const styleList = document.getElementById("style-list");
const vibeIndex = document.getElementById("vibe-index");
const yourVibe = document.getElementById("your-vibe");
const toastBox = document.getElementById("share-toast");

const make = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className: className || "", textContent: text || "" });
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const pick = (list) => list[Math.floor(Math.random() * list.length)];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// --- Mali auf der Bühne -------------------------------------------------------------------------
// Groß, atmet, zwinkert und macht ab und zu etwas Süßes: hüpfen, Herzchen, Karotte knabbern,
// Pirouette, Ohren wackeln. Klick = Freude + neuer Spruch.

const MALI_LINES = [
  "Psst … eigentlich bin ich ein Goth Baddie. Nur flauschiger. 🖤",
  "Klick auf einen Vibe – ich erklär dir alles! 🔎",
  "Mein Lieblings-Vibe? Cozy Era. Wegen der Decken. ☁️",
  "Teil die Seite mit deinen Freunden – wer ist welcher Vibe? 💬",
  "Hihi, das kitzelt! 🐰",
  "Karotten sind übrigens immer Quiet Luxury. 🥕",
];

function malipixels(canvas, grid, palette) {
  canvas.width = grid[0].length;
  canvas.height = grid.length;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  grid.forEach((row, y) => row.forEach((cell, x) => {
    if (cell === ".") return;
    ctx.fillStyle = palette[cell];
    ctx.fillRect(x, y, 1, 1);
  }));
}

function setupMali() {
  const stage = document.getElementById("styles-mali");
  const bubble = document.getElementById("styles-bubble");
  const pixels = window.mali && window.mali.pixels;
  if (!pixels) {                      // bunny.js fehlt -> wenigstens das Logo zeigen
    const logo = document.querySelector(".logo-pin");
    if (logo) stage.append(logo.cloneNode(true));
    return;
  }
  const sprite = make("canvas", "mali-sprite");
  stage.prepend(sprite);
  const show = (name) => malipixels(sprite, pixels.frames[name], pixels.palette);
  show("idle");

  let busy = false;
  const play = async (cls, ms) => {
    stage.classList.add(cls);
    await wait(ms);
    stage.classList.remove(cls);
  };
  function hearts(count = 4) {
    for (let i = 0; i < count; i++) {
      const heart = make("canvas", "mali-heart");
      malipixels(heart, pixels.heart, pixels.palette);
      heart.style.left = `${20 + Math.random() * 60}%`;
      heart.style.animationDelay = `${i * 140}ms`;
      stage.append(heart);
      setTimeout(() => heart.remove(), 2000 + i * 140);
    }
  }
  const actions = {
    async hop() { show("happy"); await play("hop", 700); show("idle"); },
    async love() { show("happy"); hearts(); await play("wiggle", 900); show("idle"); },
    async munch() {
      for (let i = 0; i < 3; i++) { show("eat1"); await wait(260); show("eat2"); await wait(260); }
      show("happy"); await wait(400); show("idle");
    },
    async twirl() { show("happy"); await play("twirl", 900); show("idle"); },
    async ears() { await play("ears", 800); },
  };
  async function act(name) {
    if (busy) return;
    busy = true;
    try { await actions[name](); } finally { busy = false; }
  }

  // Zwinkern – auch bei "weniger Bewegung", das ist ganz sanft
  (function blink() {
    setTimeout(async () => {
      if (!busy) { show("blink"); await wait(150); show("idle"); }
      blink();
    }, 2500 + Math.random() * 2500);
  })();
  // Ab und zu etwas Süßes
  if (!reduceMotion) {
    (function idle() {
      setTimeout(async () => { await act(pick(Object.keys(actions))); idle(); }, 4000 + Math.random() * 3000);
    })();
  }
  // Klick: Freude + neuer Spruch
  stage.addEventListener("click", () => {
    bubble.textContent = t(pick(MALI_LINES));
    bubble.classList.remove("pop");
    void bubble.offsetWidth;          // Animation neu starten
    bubble.classList.add("pop");
    if (!reduceMotion) act(Math.random() < 0.5 ? "love" : "hop");
  });
}

// --- Teilen -------------------------------------------------------------------------------------

function toast(text) {
  toastBox.textContent = t(text);
  toastBox.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { toastBox.hidden = true; }, 2200);
}

// Handy: Teilen-Menü (WhatsApp, Instagram …), sonst Link kopieren
async function share(data) {
  if (navigator.share) {
    try { await navigator.share(data); return; } catch (error) { if (error.name === "AbortError") return; }
  }
  try {
    await navigator.clipboard.writeText(data.url);
    toast("Link kopiert!");
  } catch {
    window.prompt(t("Link kopiert!"), data.url);
  }
}

const pageUrl = (hash = "") => `${location.origin}/stile.html${hash}`;

function shareButton(onClick) {
  const button = make("button", "share-button");
  button.type = "button";
  button.setAttribute("aria-label", t("Teilen"));
  button.title = t("Teilen");
  // Teilen-Symbol (drei verbundene Punkte) – fester Text, keine Daten von außen
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/>'
    + '<circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
    + '<path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>';
  button.addEventListener("click", onClick);
  return button;
}

// --- Inhalte -----------------------------------------------------------------------------------

function vibeCard(vibe) {
  const card = make("article", `vibe-card look-${vibe.look}`);
  card.id = vibe.slug;
  card.dataset.vibe = vibe.slug;      // eigene Farben pro Vibe (style.css)
  const head = make("header", "vibe-card-head");
  head.append(make("span", "vibe-emoji", vibe.emoji || "🖤"), make("h3", "vibe-title", vibe.title),
    shareButton(() => share({
      title: `${vibe.title} – Malipin`,
      text: t("Das ist der {title}-Vibe – schau mal, ob er zu dir passt! 🐰", { title: vibe.title }),
      url: pageUrl(`#${vibe.slug}`),
    })));
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
  yourVibe.dataset.vibe = vibe.slug;
  const actions = make("div", "your-vibe-actions");
  actions.append(Object.assign(make("a", "button", t("Mehr dazu")), { href: `#${vibe.slug}` }));
  if (window.mali && window.mali.teilen) {
    const card = make("button", "button secondary", `📸 ${t("Vibe-Karte teilen")}`);
    card.type = "button";
    card.addEventListener("click", () => window.mali.teilen(vibe));
    actions.append(card);
  }
  yourVibe.replaceChildren(
    make("p", "your-vibe-kicker", t("Dein Vibe laut Mali")),
    make("p", "your-vibe-title", `${vibe.emoji ? `${vibe.emoji} ` : ""}${vibe.title}`),
    make("p", "your-vibe-text", vibe.text),
    actions,
  );
  yourVibe.hidden = false;
}

function highlight() {
  document.querySelectorAll(".is-target").forEach((el) => el.classList.remove("is-target"));
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (!target) return;
  target.classList.add("is-target");
  target.scrollIntoView({ block: "center", behavior: "smooth" });
}

async function load() {
  setupMali();
  document.getElementById("share-page").addEventListener("click", () => share({
    title: t("Stil-Lexikon – Malipin"),
    text: t("Welcher Vibe bist du? Mali erklärt alle Pinterest-Stile 🐰"),
    url: pageUrl(),
  }));
  const data = await fetch("/api/styles").then((r) => r.json());
  for (const vibe of data.vibes) {
    vibeGrid.append(vibeCard(vibe));
    vibeIndex.append(Object.assign(make("a", "vibe-chip", `${vibe.emoji || "🖤"} ${vibe.title}`),
      { href: `#${vibe.slug}` }));
  }
  for (const style of data.styles) styleList.append(styleItem(style));
  // Mit Adresse aufgerufen (z.B. aus dem Shop: #stil-goth)? Inhalt ist erst jetzt da ->
  // hinscrollen und hervorheben (:target greift bei nachträglich eingefügten Einträgen nicht)
  highlight();
  showYourVibe(data.vibes);
}

window.addEventListener("hashchange", highlight);
load();
