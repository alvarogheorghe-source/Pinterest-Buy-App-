// Große Mali (Ganzkörper, 40 × 50 Pixel) mit Outfit, Gesichtern und Posen.
// Genutzt von der Vibe-Karte (vibecard.js) und den Social-Media-Videos (docs/social/tiktok).
// window.maliBig.draw(outfit, fur, { face, pose, cold }) -> kleines Canvas (40 × 50), groß zeichnen
// mit imageSmoothingEnabled = false. face: happy | open | shock | tired | sneeze | sad,
// pose: stand | phone (Pfoten vor dem Bauch, hält etwas), cold: rote Nase + Bäckchen.

(() => {
  // --- Große Mali für die Karte: Ganzkörper, 40 × 50 Pixel, Outfit aus den Pins --------------
  // Mali wird aus Formen zusammengesetzt (Ohren, Kopf, Körper, Arme, Beine). Jede Zelle bekommt
  // ein Kürzel; Kleidung färbt Bereiche um, der Umriss wird am Ende automatisch gezogen.
  const BIG = { w: 40, h: 50 };
  const FUR = { w: "#fffaf6", s: "#efe0d9", p: "#f6a5b9", b: "#ffc7d1", k: "#2d2326", h: "#ffffff",
    n: "#f08fac", m: "#6b5656", o: "#6b5656", c: "#ff9fb3", r: "#ff5a6e" };

  function bigMali(outfit, fur = {}, { face = "happy", pose = "stand", cold = false } = {}) {
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
    const armX = pose === "phone" ? [14.2, 25.8] : [11.6, 28.4];         // mit Handy: Arme vor dem Bauch
    const armY = pose === "phone" ? 33.5 : 34.5, pawY = pose === "phone" ? 37.2 : 39.6;
    ellipse(armX[0], armY, 2.7, 5.4, sleeves ? "A" : "w"); ellipse(armX[1], armY, 2.7, 5.4, sleeves ? "A" : "w");  // Arme
    if (top === "tee") { ellipse(armX[0], 31.5, 2.7, 2.6, "A"); ellipse(armX[1], 31.5, 2.7, 2.6, "A"); }         // kurze Ärmel
    if (pose !== "phone") { ellipse(armX[0], pawY, 2.1, 1.9, "w", false); ellipse(armX[1], pawY, 2.1, 1.9, "w", false); }  // Pfoten
    ellipse(20, 20.5, 12.4, 9.6, "w");                                                                     // Kopf
    if (!top) { for (let y = 0; y < BIG.h; y++) for (let x = 0; x < BIG.w; x++) if ("TAL".includes(g[y][x])) g[y][x] = "w"; }

    // Gesicht je nach Stimmung
    for (const ex of [15, 25]) {
      if (face === "happy") { set(ex - 1, 22, "k"); set(ex, 21, "k"); set(ex + 1, 22, "k"); set(ex - 2, 23, "k"); set(ex + 2, 23, "k"); }
      if (face === "open") { rect(ex - 1, 20, ex + 1, 23, "k"); set(ex - 1, 20, "h"); set(ex - 1, 21, "h"); }
      if (face === "shock") { rect(ex - 2, 19, ex + 2, 23, "k"); rect(ex - 2, 19, ex - 1, 20, "h"); }
      if (face === "tired") { rect(ex - 2, 22, ex + 2, 22, "k"); }
      if (face === "sneeze") { const d = ex < 20 ? 1 : -1; set(ex - 2 * d, 20, "k"); set(ex - d, 21, "k"); set(ex, 22, "k"); set(ex - d, 23, "k"); set(ex - 2 * d, 24, "k"); }
      if (face === "sad") { rect(ex - 1, 21, ex + 1, 23, "k"); set(ex - 1, 21, "h"); set(ex + (ex < 20 ? -2 : 2), 20, "k"); }
    }
    rect(11, 24, 13, 24, "b"); rect(27, 24, 29, 24, "b");
    if (cold) { rect(11, 24, 14, 25, "c"); rect(26, 24, 29, 25, "c"); }
    rect(19, 23, 20, 23, cold ? "r" : "n");
    if (face === "shock" || face === "sneeze") rect(19, 25, 21, 27, "m");
    else if (face === "sad") { set(19, 26, "m"); set(20, 25, "m"); set(21, 26, "m"); }
    else { set(19, 25, "m"); set(20, 25, "m"); }

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

  window.maliBig = { draw: bigMali, W: BIG.w, H: BIG.h };
})();
