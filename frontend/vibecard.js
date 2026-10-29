// Vibe-Karte zum Teilen 📸 – Malis Vibe-Check als Bild im Story-Format (1080 × 1920).
//
// Mali sagt dir in einer Sprechblase, welchen Vibe du hast – passend angezogen, vor einem
// Hintergrund in den Farben des Vibes. Wenige "Looks" teilen sich alle Vibes (welcher Vibe
// welchen Look hat, steht in backend/vibe.py → LOOKS). Ein Look = 2 Verlaufsfarben + ein paar
// Text-/Akzentfarben + ein kleines Pixel-Outfit, das über Mali gezeichnet wird.
//
// Wird erst geladen, wenn jemand in Malis Sprechblase auf "Vibe teilen" tippt (bunny.js).
// Das Bild entsteht komplett im Browser (Canvas) – es wird nichts hochgeladen.

(() => {
  const W = 1080;
  const H = 1920;
  const SERIF = 'Cochin, "Iowan Old Style", Georgia, serif';
  const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const SITE = "malipin.com";

  // --- Outfits: kleine Pixel-Raster, die auf Malis 16 × 16-Raster gelegt werden -------------
  // [Raster, x, y] – Position in Mali-Pixeln. "." = durchsichtig.
  const OUTFIT_COLORS = {
    K: "#241a20", S: "#c4c6cc",               // schwarz, silber
    R: "#c8693f", B: "#ecd6b3",               // rost, beige (Strickschal)
    T: "#b98a5e", t: "#6f4d33",               // Schildpatt-Spange
    G: "#1f1b2e", W: "#ffffff",               // Sonnenbrille + Glanz
    P: "#f08fac", D: "#c93a69", Y: "#d4ad4f", // rosa Schleife, Knoten, Gold
  };
  const BOW = ["xx.xx", "xxkxx", "xx.xx"];    // Schleife am rechten Ohr (x = Farbe, k = Knoten)
  const bow = (color, knot) => BOW.map((row) => row.replace(/x/g, color).replace("k", knot));

  const OUTFITS = {
    dunkel: [[["KKKKKKKKKK"], 3, 11], [["SS"], 7, 12]],                              // Choker
    erde: [[["RRBBRRBBRRBB", "BBRRBBRRBBRR"], 2, 11], [["RR", "BB", "RR"], 10, 13]], // Strickschal
    clean: [[["TtTt", "tTtT"], 6, 4]],                                                // Haarspange
    street: [[["GGGGGGGGGG", ".WG....WG."], 3, 8]],                                   // Sonnenbrille
    romantisch: [[bow("P", "D"), 11, 0], [[".YYYYYY.", "...YY..."], 4, 12]],         // Schleife + Kette
    rosa: [],
  };

  // --- Hintergründe & Farben pro Look ---------------------------------------------------------
  const LOOKS = {
    rosa: { bg: ["#fff8fa", "#fbd3df"], text: "#3a2a30", muted: "#7a606a", accent: "#c93a69",
      title: "#c93a69", cta: "#c93a69", ctaText: "#ffffff", deco: "#ff6b8b" },
    dunkel: { bg: ["#3d2836", "#120d12"], text: "#fbe3ea", muted: "#cdb0bc", accent: "#ff8fb4",
      title: "#3d2836", cta: "#ff8fb4", ctaText: "#1a1216", deco: "#ff8fb4",
      fur: { p: "#7d3f72", b: "#a8719e" } },  // Mali mit dunkelvioletten Ohren & Bäckchen
    erde: { bg: ["#f5eee2", "#c9d1b4"], text: "#3b2f26", muted: "#66574a", accent: "#8f5431",
      title: "#8f5431", cta: "#8f5431", ctaText: "#ffffff", deco: "#c8693f" },
    clean: { bg: ["#ffffff", "#ece3d7"], text: "#3a3330", muted: "#6f655f", accent: "#7d6a59",
      title: "#3a3330", cta: "#7d6a59", ctaText: "#ffffff", deco: "#d8c3a5" },
    street: { bg: ["#eef0ff", "#b9bdf3"], text: "#22203a", muted: "#4f4c75", accent: "#4b45b8",
      title: "#4b45b8", cta: "#4b45b8", ctaText: "#ffffff", deco: "#7b75e0" },
    romantisch: { bg: ["#fff5f3", "#f6c3cd"], text: "#3a2a30", muted: "#7a606a", accent: "#c93a69",
      title: "#c93a69", cta: "#c93a69", ctaText: "#ffffff", deco: "#e8789a" },
  };

  // --- Große Mali für die Karte: Ganzkörper, 40 × 50 Pixel, Outfit aus den Pins --------------
  // Mali wird aus Formen zusammengesetzt (Ohren, Kopf, Körper, Arme, Beine). Jede Zelle bekommt
  // ein Kürzel; Kleidung färbt Bereiche um, der Umriss wird am Ende automatisch gezogen.
  const BIG = { w: 40, h: 50 };
  const FUR = { w: "#fffaf6", s: "#efe0d9", p: "#f6a5b9", b: "#ffc7d1", k: "#2d2326", h: "#ffffff",
    n: "#f08fac", m: "#6b5656", o: "#6b5656" };

  function bigMali(outfit, fur = {}) {
    const g = Array.from({ length: BIG.h }, () => Array(BIG.w).fill("."));
    const set = (x, y, c) => { if (x >= 0 && y >= 0 && x < BIG.w && y < BIG.h) g[y][x] = c; };
    const ellipse = (cx, cy, rx, ry, c, shade = true) => {
      for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) {
        for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
          const d = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2;
          if (d > 1) continue;
          const edge = shade && d > 0.62 && (x + 0.5 - cx) / rx + (y + 0.5 - cy) / ry > 0.55;
          set(x, y, edge && c === "w" ? "s" : c);
        }
      }
    };
    const rect = (x0, y0, x1, y1, c) => { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) set(x, y, c); };
    const o = outfit || {};
    const top = o.garment;
    const sleeves = top && top !== "tee" && top !== "dress";

    // Körper (von hinten nach vorn)
    ellipse(13.5, 9, 3.4, 8.6, "w"); ellipse(26.5, 9, 3.4, 8.6, "w");          // Ohren
    ellipse(13.5, 9.5, 1.6, 6.2, "p", false); ellipse(26.5, 9.5, 1.6, 6.2, "p", false);
    rect(15, 40, 18, 45, top === "dress" ? "w" : "L"); rect(22, 40, 25, 45, top === "dress" ? "w" : "L");  // Beine
    ellipse(16.5, 46.6, 3.4, 1.9, "F", false); ellipse(23.5, 46.6, 3.4, 1.9, "F", false);                 // Schuhe
    ellipse(20, 35, 8.2, 7.2, "T");                                                                        // Bauch
    if (top === "dress") {                                                                                 // Rock
      for (let y = 37; y <= 44; y++) { const half = 6 + (y - 37) * 0.75; rect(Math.round(20 - half), y, Math.round(19 + half), y, "T"); }
    }
    ellipse(11.6, 34.5, 2.7, 5.4, sleeves ? "A" : "w"); ellipse(28.4, 34.5, 2.7, 5.4, sleeves ? "A" : "w");  // Arme
    if (top === "tee") { ellipse(11.6, 31.5, 2.7, 2.6, "A"); ellipse(28.4, 31.5, 2.7, 2.6, "A"); }         // kurze Ärmel
    ellipse(11.6, 39.6, 2.1, 1.9, "w", false); ellipse(28.4, 39.6, 2.1, 1.9, "w", false);                  // Pfoten
    ellipse(20, 20.5, 12.4, 9.6, "w");                                                                     // Kopf
    if (!top) { for (let y = 0; y < BIG.h; y++) for (let x = 0; x < BIG.w; x++) if ("TAL".includes(g[y][x])) g[y][x] = "w"; }

    // Gesicht: fröhliche Augen (^ ^) mit Glanz, Bäckchen, Näschen, kleiner Mund
    for (const ex of [15, 25]) { set(ex - 1, 22, "k"); set(ex, 21, "k"); set(ex + 1, 22, "k"); set(ex - 2, 23, "k"); set(ex + 2, 23, "k"); }
    rect(11, 24, 13, 24, "b"); rect(27, 24, 29, 24, "b");
    rect(19, 23, 20, 23, "n");
    set(19, 25, "m"); set(20, 25, "m");

    // Kleidung im Detail
    const C = { T: o.color, A: o.color, L: o.pants || "#55688f", F: o.shoes || "#fbfaf7", d: o.shade, a: o.accent, e: "#fbf6ef" };
    if (top === "hoodie") { rect(18, 30, 18, 33, "e"); rect(22, 30, 22, 33, "e"); rect(16, 36, 24, 38, "d"); }
    if (top === "jacket") { rect(19, 29, 21, 41, "e"); for (let y = 29; y <= 33; y++) { set(18 - (y - 29) % 2, y, "d"); set(22 + (y - 29) % 2, y, "d"); } }
    if (top === "blazer") { for (let y = 29; y <= 33; y++) rect(20 - (33 - y) / 2 | 0, y, 20 + (33 - y) / 2 | 0, y, "e"); set(20, 36, "d"); set(20, 39, "d"); }
    if (top === "knit") { for (let y = 29; y < 43; y++) for (let x = 0; x < BIG.w; x++) if ((g[y][x] === "T" || g[y][x] === "A") && (x + y) % 3 === 0) g[y][x] = "d"; }
    if (top === "dress") { for (let y = 38; y <= 44; y += 3) for (let x = 13; x <= 27; x += 3) if (g[y][x] === "T") g[y][x] = "e"; }
    if (o.shoes && o.shoes !== "#fbfaf7") rect(15, 44, 18, 45, "F"), rect(22, 44, 25, 45, "F");   // Boots
    else { for (const x of [14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26]) set(x, 48, "z"); }       // Sohle

    // Accessoires
    const PAL2 = { G: "#1f1b2e", W: "#ffffff", K: "#241a20", S: "#c4c6cc", Y: "#d4ad4f", P: "#f08fac", D: "#c93a69",
      t: "#6f4d33", u: "#b98a5e", f: "#ffd1dc", q: "#ffe066", v: "#7a9e7e" };
    for (const acc of o.accessories || []) {
      if (acc === "sunglasses") { rect(12, 21, 17, 23, "G"); rect(22, 21, 27, 23, "G"); rect(18, 21, 21, 21, "G"); set(13, 21, "W"); set(23, 21, "W"); }
      if (acc === "glasses") { for (const ex of [15, 25]) { rect(ex - 3, 20, ex + 3, 20, "t"); rect(ex - 3, 24, ex + 3, 24, "t"); rect(ex - 3, 20, ex - 3, 24, "t"); rect(ex + 3, 20, ex + 3, 24, "t"); } rect(19, 21, 21, 21, "t"); }
      if (acc === "choker") { rect(14, 29, 26, 29, "K"); set(20, 30, "S"); }
      if (acc === "pearls") { for (let x = 15; x <= 25; x += 2) set(x, 30, "W"); }
      if (acc === "goldchain") { rect(16, 31, 24, 31, "Y"); set(20, 32, "Y"); }
      if (acc === "silverchain") { rect(16, 31, 24, 31, "S"); set(20, 32, "S"); }
      if (acc === "scarf") { rect(12, 28, 28, 30, "a"); for (let x = 13; x <= 27; x += 3) set(x, 29, "d"); rect(24, 31, 26, 36, "a"); }
      if (acc === "bow") { rect(25, 1, 26, 3, "P"); rect(29, 1, 30, 3, "P"); rect(27, 2, 28, 2, "D"); }
      if (acc === "hairclip") { rect(15, 13, 18, 13, "u"); set(16, 13, "t"); set(18, 13, "t"); }
      if (acc === "flowers") { for (let x = 10; x <= 30; x += 4) { set(x, 12, "f"); set(x + 1, 12, "q"); set(x + 2, 12, "v"); } }
      if (acc === "headband") { rect(9, 14, 31, 15, "a"); }
      if (acc === "beanie") { for (let y = 10; y <= 15; y++) for (let x = 8; x <= 32; x++) if (g[y][x] !== "." && g[y][x] !== "p") g[y][x] = y === 15 ? "d" : "a"; }
      if (acc === "bag") { for (let i = 0; i < 9; i++) set(17 + i, 29 + i, "K"); rect(28, 38, 33, 42, "a"); rect(28, 38, 33, 38, "d"); }
    }

    // Umriss: jede leere Zelle neben Mali wird dunkel
    const filled = (x, y) => x >= 0 && y >= 0 && x < BIG.w && y < BIG.h && g[y][x] !== "." && g[y][x] !== "O";
    for (let y = 0; y < BIG.h; y++) for (let x = 0; x < BIG.w; x++) {
      if (g[y][x] === "." && (filled(x - 1, y) || filled(x + 1, y) || filled(x, y - 1) || filled(x, y + 1))) g[y][x] = "O";
    }
    // Kleidungskanten etwas dunkler (sieht nach Stoff aus)
    const cloth = (c) => c === "T" || c === "A";
    for (let y = 0; y < BIG.h; y++) for (let x = 0; x < BIG.w; x++) {
      if (cloth(g[y][x]) && [[1, 0], [-1, 0], [0, 1]].some(([dx, dy]) => "wsO".includes((g[y + dy] || [])[x + dx] || "."))) g[y][x] = "d";
    }
    const palette = { ...FUR, ...fur, O: FUR.o, z: "#9b8f88", ...PAL2, ...C };
    const canvas = document.createElement("canvas");
    canvas.width = BIG.w; canvas.height = BIG.h;
    const c = canvas.getContext("2d");
    g.forEach((row, y) => row.forEach((cell, x) => { if (palette[cell]) { c.fillStyle = palette[cell]; c.fillRect(x, y, 1, 1); } }));
    return canvas;
  }

  // --- Zeichnen ------------------------------------------------------------------------------

  // Pixel-Raster groß zeichnen: jedes Pixel = size × size. Zeilen dürfen Text oder Arrays sein.
  function drawPixels(ctx, grid, palette, x, y, size) {
    grid.forEach((row, gy) => [...row].forEach((cell, gx) => {
      if (cell === "." || !palette[cell]) return;
      ctx.fillStyle = palette[cell];
      ctx.fillRect(x + gx * size, y + gy * size, size, size);
    }));
  }

  // Text in Zeilen umbrechen, die höchstens maxWidth breit sind
  function wrap(ctx, text, maxWidth) {
    const lines = [];
    let line = "";
    for (const word of text.split(" ")) {
      const test = line ? `${line} ${word}` : word;
      if (ctx.measureText(test).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // Schriftgröße verkleinern, bis das längste Wort in die Breite passt
  function fitFont(ctx, text, weight, start, min, maxWidth, family) {
    let size = start;
    const longest = () => Math.max(...text.split(" ").map((w) => ctx.measureText(w).width));
    ctx.font = `${weight} ${size}px ${family}`;
    while (longest() > maxWidth && size > min) {
      size -= 4;
      ctx.font = `${weight} ${size}px ${family}`;
    }
    return size;
  }

  function draw(vibe, pixels) {
    const look = LOOKS[vibe.look] || LOOKS.rosa;
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.textAlign = "center";

    // Hintergrund im Farbverlauf des Looks
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, look.bg[0]);
    bg.addColorStop(1, look.bg[1]);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // Verstreute Pixel-Herzen in der Deko-Farbe
    ctx.globalAlpha = 0.2;
    const heartPalette = { r: look.deco };
    for (const [x, y, size] of [[90, 260, 9], [935, 300, 12], [60, 1180, 10], [960, 1040, 8],
      [70, 1560, 12], [965, 1480, 10], [840, 110, 7]]) {
      drawPixels(ctx, pixels.heart, heartPalette, x, y, size);
    }
    ctx.globalAlpha = 1;

    // Kopf: "malipin" + "MEIN PINTEREST-VIBE"
    ctx.textAlign = "left";
    ctx.font = `700 64px ${SERIF}`;
    const wMali = ctx.measureText("mali").width;
    ctx.font = `italic 700 64px ${SERIF}`;
    const startX = W / 2 - (wMali + ctx.measureText("pin").width) / 2;
    ctx.font = `700 64px ${SERIF}`;
    ctx.fillStyle = look.text;
    ctx.fillText("mali", startX, 150);
    ctx.font = `italic 700 64px ${SERIF}`;
    ctx.fillStyle = look.accent;
    ctx.fillText("pin", startX + wMali, 150);
    ctx.textAlign = "center";
    ctx.font = `600 32px ${SANS}`;
    ctx.fillStyle = look.muted;
    ctx.fillText(t("MEIN PINTEREST-VIBE"), W / 2, 222);

    // --- Mali groß in der Mitte, mit Lichtschein ---
    const cell = 16;
    const malW = BIG.w * cell, malH = BIG.h * cell;
    const malX = Math.round((W - malW) / 2), malTop = 235;
    const glow = ctx.createRadialGradient(W / 2, malTop + malH * 0.5, 40, W / 2, malTop + malH * 0.5, 480);
    glow.addColorStop(0, vibe.look === "dunkel" ? "rgba(255,143,180,0.22)" : "rgba(255,255,255,0.75)");
    glow.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, malTop - 120, W, malH + 240);
    ctx.fillStyle = "rgba(0,0,0,0.12)";
    ctx.beginPath(); ctx.ellipse(W / 2, malTop + malH - 24, 250, 32, 0, 0, Math.PI * 2); ctx.fill();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(bigMali(vibe.outfit, look.fur), malX, malTop, malW, malH);
    ctx.fillStyle = look.deco;                                      // Funkeln
    for (const [x, y, s] of [[malX - 10, malTop + 90, 11], [malX + malW + 10, malTop + 40, 13], [malX + malW - 10, malTop + 300, 9], [malX + 20, malTop + 360, 8]]) {
      ctx.fillRect(x, y - s * 2, s, s * 5); ctx.fillRect(x - s * 2, y, s * 5, s);
    }

    // --- "Du bist" + Vibe ---
    let y = malTop + malH + 60;
    ctx.font = `600 38px ${SANS}`;
    ctx.fillStyle = look.muted;
    ctx.fillText(t("Du bist"), W / 2, y);
    const titleSize = fitFont(ctx, vibe.title, 700, 116, 60, W - 160, SERIF);
    ctx.font = `700 ${titleSize}px ${SERIF}`;
    ctx.fillStyle = look.accent;
    for (const line of wrap(ctx, vibe.title, W - 160)) { y += titleSize * 1.0; ctx.fillText(line, W / 2, y); }

    // --- drei Eigenschaften ---
    if (vibe.traits && vibe.traits.length) {
      y += 110;
      let fontSize = 38;
      const gap = 16;
      const widths = () => vibe.traits.map((trait) => { ctx.font = `700 ${fontSize}px ${SANS}`; return ctx.measureText(trait).width + fontSize * 1.3; });
      while (widths().reduce((a, b) => a + b, 0) + gap * 2 > W - 120 && fontSize > 26) fontSize -= 2;
      const ws = widths();
      let x = (W - ws.reduce((a, b) => a + b, 0) - gap * 2) / 2;
      vibe.traits.forEach((trait, i) => {
        ctx.fillStyle = "rgba(255,255,255,0.88)";
        roundRect(ctx, x, y - fontSize * 1.05, ws[i], fontSize * 1.8, fontSize * 0.9);
        ctx.fill();
        ctx.font = `700 ${fontSize}px ${SANS}`;
        ctx.fillStyle = "#3a2a30";
        ctx.fillText(trait, x + ws[i] / 2, y);
        x += ws[i] + gap;
      });
    }

    // --- Farben (nur Punkte) + Duo ---
    const colors = (vibe.colors || []).slice(0, 4);
    if (colors.length) {
      y += 120;
      const x0 = W / 2 - ((colors.length - 1) * 90) / 2;
      colors.forEach((color, i) => {
        ctx.beginPath(); ctx.arc(x0 + i * 90, y, 30, 0, Math.PI * 2);
        ctx.fillStyle = color.hex; ctx.fill();
        ctx.lineWidth = 5; ctx.strokeStyle = "rgba(255,255,255,0.9)"; ctx.stroke();
      });
    }
    if (vibe.duo && y + 100 < H - 220) {
      y += 104;
      ctx.font = `600 36px ${SANS}`;
      ctx.fillStyle = look.text;
      ctx.fillText(t("Perfektes Duo mit {duo}", { duo: vibe.duo }), W / 2, y);
    }

    // Fuß: Einladung
    ctx.fillStyle = look.cta;
    roundRect(ctx, 140, H - 200, W - 280, 104, 52);
    ctx.fill();
    ctx.font = `700 40px ${SANS}`;
    ctx.fillStyle = look.ctaText;
    ctx.fillText(t("Finde deinen Vibe → {site}", { site: SITE }), W / 2, H - 134);

    return canvas;
  }

  // --- Vorschau + Teilen -----------------------------------------------------------------------

  function toBlob(canvas) {
    return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  }

  function download(blob, filename) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  async function open(vibe, pixels) {
    const canvas = draw(vibe, pixels);
    const blob = await toBlob(canvas);
    const filename = `malipin-vibe-${vibe.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`;
    const file = new File([blob], filename, { type: "image/png" });
    const canShare = Boolean(navigator.canShare && navigator.canShare({ files: [file] }));

    const overlay = document.createElement("div");
    overlay.className = "vibecard-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-label", t("Deine Vibe-Karte"));
    const box = document.createElement("div");
    box.className = "vibecard-box";
    const img = Object.assign(document.createElement("img"), {
      src: URL.createObjectURL(blob),
      alt: t("Vibe-Karte: {title}", { title: vibe.title }),
      className: "vibecard-image",
    });
    const actions = document.createElement("div");
    actions.className = "vibecard-actions";

    const share = Object.assign(document.createElement("button"), {
      className: "button", textContent: canShare ? "Teilen" : "Bild speichern",
    });
    share.addEventListener("click", async () => {
      if (!canShare) return download(blob, filename);
      try {
        await navigator.share({
          files: [file],
          title: "Mein Malipin-Vibe",
          text: t("Mein Pinterest-Vibe ist {title}. Finde deinen auf {site}", { title: vibe.title, site: SITE }),
        });
      } catch (error) {
        // Abgebrochen ist okay; bei anderen Fehlern einfach herunterladen
        if (error.name !== "AbortError") download(blob, filename);
      }
    });
    const close = Object.assign(document.createElement("button"), {
      className: "button secondary", textContent: "Schließen",
    });

    function closeOverlay() {
      URL.revokeObjectURL(img.src);
      overlay.remove();
      document.removeEventListener("keydown", onKey);
    }
    function onKey(event) {
      if (event.key === "Escape") closeOverlay();
    }
    close.addEventListener("click", closeOverlay);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) closeOverlay(); });
    document.addEventListener("keydown", onKey);

    actions.append(share, close);
    box.append(img, actions);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    share.focus();
  }

  window.vibeCard = { open, draw };
})();
