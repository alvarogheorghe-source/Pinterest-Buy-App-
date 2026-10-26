// Erzeugt die SEO-Bilder in frontend/img/ (einmalig, die Ergebnisse liegen im Repo):
//   og-image.png          1200×630  Vorschau beim Teilen (WhatsApp, Pinterest, X …)
//   og-image-en.png       1200×630  dasselbe auf Englisch (/en/)
//   apple-touch-icon.png  180×180   Symbol auf dem iPhone-Homescreen
//   icon-192.png / icon-512.png     Android / Web-Manifest / Logo für Google
//   favicon-48.png        48×48     Suchergebnis-Symbol bei Google
//
// Starten (braucht Node + Playwright):   node scripts/make_seo_images.mjs
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");

const img = (name) => fileURLToPath(new URL(`../frontend/img/${name}`, import.meta.url));
const mali = "data:image/svg+xml;base64," + readFileSync(img("favicon.svg")).toString("base64");
const serif = `'Cochin', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif`;

const icon = (size, padding, background, radius) => `
  <body style="margin:0;width:${size}px;height:${size}px;display:grid;place-items:center;
               background:${background};border-radius:${radius}">
    <img src="${mali}" style="width:${size - 2 * padding}px;height:${size - 2 * padding}px;
         image-rendering:pixelated">
  </body>`;

const tiles = [["#f8c9d7", "#ec9ab4", 150], ["#dccbf0", "#b39ad8", 110], ["#fbe6dc", "#efc3b5", 130],
               ["#8e3b5c", "#5e2840", 120], ["#f6b49a", "#e5807a", 160], ["#fff1d8", "#f6d8b8", 100]];
const og = (t) => `
  <body style="margin:0;width:1200px;height:630px;overflow:hidden;position:relative;
               font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#3a2a30;
               background:radial-gradient(circle at 15% 20%,#ffe0ea 0,transparent 45%),
                          radial-gradient(circle at 85% 80%,#eadcf8 0,transparent 45%),#fff8fa">
    <div style="position:absolute;left:72px;top:64px;width:540px">
      <div style="display:flex;align-items:center;gap:18px">
        <img src="${mali}" style="width:76px;height:76px;image-rendering:pixelated">
        <span style="font:700 54px ${serif}">mali<span style="color:#c93a69;font-style:italic">pin</span></span>
      </div>
      <h1 style="font:700 66px/1.05 ${serif};margin:46px 0 0">${t.headline}<br>
        <em style="color:#c93a69">${t.accent}</em></h1>
      <p style="font-size:27px;line-height:1.4;color:#7a606a;margin:28px 0 0">${t.lead}</p>
    </div>
    <div style="position:absolute;right:64px;top:70px;width:400px;columns:3;column-gap:12px;
                padding:16px;background:#fff;border-radius:22px;transform:rotate(3deg);
                box-shadow:0 24px 60px rgba(58,42,48,.16)">
      ${tiles.map(([a, b, h]) => `<div style="height:${h}px;margin-bottom:12px;border-radius:14px;
          break-inside:avoid;background:linear-gradient(160deg,${a},${b})"></div>`).join("")}
    </div>
    <div style="position:absolute;right:320px;bottom:48px;background:#fff;border-radius:18px;
                padding:14px 18px 16px;width:210px;transform:rotate(-4deg);
                box-shadow:0 18px 40px rgba(58,42,48,.18)">
      <div style="height:110px;border-radius:12px;background:linear-gradient(160deg,#fbe6dc,#efc3b5)"></div>
      <p style="margin:12px 0 2px;font-size:13px;letter-spacing:.08em;color:#7a606a">EBAY · SECOND HAND</p>
      <p style="margin:0;font-size:20px;font-weight:600">Baggy Jeans Light Wash</p>
      <p style="margin:4px 0 0;font-size:20px;font-weight:700">€ 24,90</p>
    </div>
  </body>`;

const TEXTS = {
  de: { headline: "Dein Pinterest.<br>Dein Stil.", accent: "Zum kleinen Preis.",
        lead: "Outfits &amp; Deko passend zu deinem Pinterest-Stil – neu und Second Hand." },
  en: { headline: "Your Pinterest.<br>Your style.", accent: "At a small price.",
        lead: "Outfits &amp; decor that match your Pinterest style – new and second hand." },
};

const jobs = [
  ["og-image.png", og(TEXTS.de), 1200, 630],
  ["og-image-en.png", og(TEXTS.en), 1200, 630],
  ["apple-touch-icon.png", icon(180, 24, "#fff8fa", "0"), 180, 180],
  // Android schneidet Symbole rund zu ("maskable") -> genug Rand lassen
  ["icon-192.png", icon(192, 36, "#fde9ef", "0"), 192, 192],
  ["icon-512.png", icon(512, 96, "#fde9ef", "0"), 512, 512],
  ["favicon-48.png", icon(48, 2, "transparent", "0"), 48, 48],
];

const browser = await chromium.launch();
for (const [name, html, width, height] of jobs) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"></head>${html}</html>`);
  await page.waitForTimeout(200);
  await page.screenshot({ path: img(name), omitBackground: name === "favicon-48.png" });
  console.log("fertig:", name);
}
await browser.close();
