// "Mali hat mein Fit gefunden" 📸 – das Ergebnis der Foto-Suche als Story-Bild (1080 × 1920):
// dein Foto, was Mali darauf sieht, drei Treffer mit Preis und malipin.com.
// Entsteht komplett im Browser (Canvas), geteilt wird über share.js. Nichts wird hochgeladen.

(() => {
  const W = 1080;
  const H = 1920;
  const SERIF = 'Cochin, "Iowan Old Style", Georgia, serif';
  const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const SITE = "malipin.com";
  const PINK = "#c93a69";
  const TEXT = "#3a2a30";
  const MUTED = "#7a606a";

  // Bild laden. Produktbilder anderer Shops nur mit CORS-Freigabe – ohne die bliebe die
  // Leinwand "verschmutzt" und ließe sich nicht speichern. Dann eben ohne Bild (null).
  function loadImage(src, crossOrigin = true) {
    return new Promise((resolve) => {
      const img = new Image();
      if (crossOrigin) img.crossOrigin = "anonymous";
      const timer = setTimeout(() => resolve(null), 4000);
      img.onload = () => { clearTimeout(timer); resolve(img); };
      img.onerror = () => { clearTimeout(timer); resolve(null); };
      img.src = src;
    });
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

  // Bild füllt den Rahmen, überstehende Ränder werden abgeschnitten (wie CSS object-fit: cover)
  function cover(ctx, img, x, y, w, h, r) {
    const scale = Math.max(w / img.width, h / img.height);
    const sw = w / scale;
    const sh = h / scale;
    ctx.save();
    roundRect(ctx, x, y, w, h, r);
    ctx.clip();
    ctx.drawImage(img, (img.width - sw) / 2, (img.height - sh) / 2, sw, sh, x, y, w, h);
    ctx.restore();
  }

  // Text auf höchstens `lines` Zeilen umbrechen, sonst mit … kürzen
  function lines(ctx, text, maxWidth, max) {
    const words = text.split(/\s+/);
    const result = [];
    let line = "";
    for (const word of words) {
      const next = line ? `${line} ${word}` : word;
      if (ctx.measureText(next).width <= maxWidth) { line = next; continue; }
      if (line) result.push(line);
      line = word;
      if (result.length === max) break;
    }
    if (result.length < max && line) result.push(line);
    if (result.length === max && words.join(" ") !== result.join(" ")) {
      let last = result[max - 1];
      while (last && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
      result[max - 1] = `${last}…`;
    }
    return result.slice(0, max);
  }

  async function draw(photoBlob, data) {
    const canvas = Object.assign(document.createElement("canvas"), { width: W, height: H });
    const ctx = canvas.getContext("2d");
    const products = data.products.slice(0, 3);
    const [photo, logo, ...images] = await Promise.all([
      loadImage(URL.createObjectURL(photoBlob), false),
      loadImage("/img/favicon.svg", false),
      ...products.map((p) => loadImage(p.image_url)),
    ]);

    // Hintergrund
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, "#fff8fa");
    bg.addColorStop(1, "#fbd3df");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // Kopf: Mali + malipin
    ctx.imageSmoothingEnabled = false;
    if (logo) ctx.drawImage(logo, 380, 86, 76, 76);
    ctx.imageSmoothingEnabled = true;
    ctx.fillStyle = TEXT;
    ctx.font = `600 58px ${SERIF}`;
    ctx.textBaseline = "middle";
    ctx.fillText("mali", 470, 126);
    ctx.fillStyle = PINK;
    ctx.font = `italic 600 58px ${SERIF}`;
    ctx.fillText("pin", 470 + ctx.measureText("mali").width + 2, 126);

    // Titel
    ctx.textAlign = "center";
    ctx.fillStyle = TEXT;
    ctx.font = `700 76px ${SERIF}`;
    ctx.fillText(t("Mali hat mein Fit gefunden"), W / 2, 262, W - 120);

    // Dein Foto
    const px = 210;
    const py = 350;
    const pw = 660;
    const ph = 800;
    ctx.save();
    ctx.shadowColor = "rgba(150, 40, 80, 0.25)";
    ctx.shadowBlur = 40;
    ctx.shadowOffsetY = 16;
    ctx.fillStyle = "#ffffff";
    roundRect(ctx, px - 14, py - 14, pw + 28, ph + 28, 44);
    ctx.fill();
    ctx.restore();
    if (photo) cover(ctx, photo, px, py, pw, ph, 32);
    URL.revokeObjectURL(photo?.src || "");

    // Was Mali sieht (Chips)
    const f = data.found || {};
    const seen = [...(f.categories || []), ...(f.colors || []), ...(f.styles || [])]
      .map((term) => t(term)).filter((term, i, all) => all.indexOf(term) === i).slice(0, 4);
    ctx.font = `600 34px ${SANS}`;
    const chipWidths = seen.map((term) => ctx.measureText(term).width + 52);
    let cx = (W - (chipWidths.reduce((a, b) => a + b, 0) + 16 * (seen.length - 1))) / 2;
    for (const [i, term] of seen.entries()) {
      ctx.fillStyle = "#ffffff";
      roundRect(ctx, cx, 1205, chipWidths[i], 64, 32);
      ctx.fill();
      ctx.fillStyle = PINK;
      ctx.fillText(term, cx + chipWidths[i] / 2, 1238);
      cx += chipWidths[i] + 16;
    }

    // Drei Treffer
    const cw = 300;
    const gap = 30;
    const startX = (W - (products.length * cw + (products.length - 1) * gap)) / 2;
    for (const [i, product] of products.entries()) {
      const x = startX + i * (cw + gap);
      const y = 1300;
      const image = images[i];
      const imageH = 280;
      ctx.fillStyle = "#ffffff";
      roundRect(ctx, x, y, cw, imageH + 170, 28);
      ctx.fill();
      if (image) {
        cover(ctx, image, x, y, cw, imageH, 28);
      } else {
        // Shop erlaubt das Bild nicht auf der Leinwand -> rosa Fläche mit Mali, gleich hoch
        ctx.save();
        roundRect(ctx, x, y, cw, imageH, 28);
        ctx.clip();
        const soft = ctx.createLinearGradient(x, y, x, y + imageH);
        soft.addColorStop(0, "#fde4ec");
        soft.addColorStop(1, "#f6c3d2");
        ctx.fillStyle = soft;
        ctx.fillRect(x, y, cw, imageH);
        ctx.restore();
        if (logo) {
          ctx.imageSmoothingEnabled = false;
          ctx.drawImage(logo, x + cw / 2 - 60, y + imageH / 2 - 60, 120, 120);
          ctx.imageSmoothingEnabled = true;
        }
      }
      ctx.textAlign = "left";
      ctx.fillStyle = TEXT;
      ctx.font = `500 28px ${SANS}`;
      lines(ctx, product.name, cw - 40, 2).forEach((line, n) => ctx.fillText(line, x + 20, y + imageH + 40 + n * 36));
      ctx.fillStyle = PINK;
      ctx.font = `700 34px ${SANS}`;
      ctx.fillText(money(product), x + 20, y + imageH + 132);
      ctx.textAlign = "center";
    }

    // Aufruf unten
    ctx.font = `700 44px ${SANS}`;
    const cta = t("Finde dein Fit auf {site}", { site: SITE });
    const ctaW = ctx.measureText(cta).width + 100;
    ctx.fillStyle = PINK;
    roundRect(ctx, (W - ctaW) / 2, 1790, ctaW, 96, 48);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.fillText(cta, W / 2, 1840);
    return canvas;
  }

  async function open(photoBlob, data) {
    window.shareImage(await draw(photoBlob, data), {
      filename: "malipin-fit.png",
      title: "Malipin",
      text: t("Mali hat mein Fit gefunden. Finde deins auf {site}", { site: SITE }),
      alt: t("Malis Fund zu meinem Foto"),
    });
  }

  window.fitCard = { open, draw };
})();
