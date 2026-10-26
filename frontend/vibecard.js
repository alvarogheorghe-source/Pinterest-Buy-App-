// Vibe-Karte zum Teilen 📸 – Malis Vibe-Check als Bild im Story-Format (1080 × 1920).
//
// Wird erst geladen, wenn jemand in Malis Sprechblase auf "Vibe teilen" tippt (bunny.js).
// Das Bild entsteht komplett im Browser (Canvas) – es wird nichts hochgeladen.
// Teilen: Auf dem Handy öffnet sich das normale Teilen-Menü (Instagram, TikTok, WhatsApp …),
// am Computer wird das Bild heruntergeladen.

(() => {
  const W = 1080;
  const H = 1920;
  const SERIF = 'Cochin, "Iowan Old Style", Georgia, serif';
  const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const COLORS = { text: "#3a2a30", muted: "#7a606a", accent: "#c93a69", soft: "#fbe3ea" };
  const SITE = "malipin.com";

  // --- Zeichnen ------------------------------------------------------------------------------

  // Pixel-Raster (wie in bunny.js) groß zeichnen: jedes Pixel = size × size
  function drawPixels(ctx, grid, palette, x, y, size) {
    grid.forEach((row, gy) => row.forEach((cell, gx) => {
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

  function draw(vibe, pixels) {
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";

    // Hintergrund: zartes Rosa-Verlauf
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, "#fff8fa");
    bg.addColorStop(1, "#fbd3df");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // Verstreute Pixel-Herzen (immer gleich verteilt, damit es ruhig aussieht)
    ctx.globalAlpha = 0.18;
    const hearts = [[90, 210, 9], [930, 330, 12], [140, 1260, 10], [905, 1150, 8],
      [60, 1520, 12], [960, 1440, 10], [820, 120, 7]];
    for (const [x, y, size] of hearts) drawPixels(ctx, pixels.heart, pixels.palette, x, y, size);
    ctx.globalAlpha = 1;

    // Kopf: "malipin" + kleiner Hinweis
    ctx.font = `700 64px ${SERIF}`;
    const mali = "mali";
    const pin = "pin";
    const wMali = ctx.measureText(mali).width;
    ctx.font = `italic 700 64px ${SERIF}`;
    const wPin = ctx.measureText(pin).width;
    const startX = W / 2 - (wMali + wPin) / 2;
    ctx.textAlign = "left";
    ctx.font = `700 64px ${SERIF}`;
    ctx.fillStyle = COLORS.text;
    ctx.fillText(mali, startX, 170);
    ctx.font = `italic 700 64px ${SERIF}`;
    ctx.fillStyle = COLORS.accent;
    ctx.fillText(pin, startX + wMali, 170);
    ctx.textAlign = "center";

    ctx.font = `600 34px ${SANS}`;
    ctx.fillStyle = COLORS.muted;
    ctx.fillText("MEIN PINTEREST-VIBE", W / 2, 250);

    // Großer, glücklicher Mali (16 × 16 Pixel × 24)
    const size = 24;
    const spriteW = pixels.happy[0].length * size;
    drawPixels(ctx, pixels.happy, pixels.palette, (W - spriteW) / 2, 300, size);
    // Herz über Malis Kopf
    drawPixels(ctx, pixels.heart, pixels.palette, W / 2 + 140, 285, 14);

    // Emoji + Titel
    let y = 840;
    ctx.font = `130px ${SANS}`;
    ctx.fillText(vibe.emoji, W / 2, y);
    y += 145;
    // Titel: lange Wörter ("Clean-Girl-Aesthetic") lassen sich nicht umbrechen -> kleiner
    let titleSize = 104;
    const longestWord = () => Math.max(...vibe.title.split(" ").map((w) => ctx.measureText(w).width));
    ctx.font = `700 ${titleSize}px ${SERIF}`;
    while (longestWord() > W - 160 && titleSize > 56) {
      titleSize -= 4;
      ctx.font = `700 ${titleSize}px ${SERIF}`;
    }
    ctx.fillStyle = COLORS.text;
    for (const line of wrap(ctx, vibe.title, W - 160)) {
      ctx.fillText(line, W / 2, y);
      y += titleSize * 1.08;
    }
    if (vibe.second) {
      ctx.font = `italic 44px ${SERIF}`;
      ctx.fillStyle = COLORS.accent;
      ctx.fillText(`… mit einer Prise ${vibe.second}`, W / 2, y);
      y += 70;
    }

    // Malis Spruch in einer weißen Sprechblase
    ctx.font = `40px ${SANS}`;
    // So viele Zeilen, wie über dem Button Platz haben (2–4); sonst gekürzt mit "…"
    const room = Math.floor((H - 290 - (y + 20) - 80) / 56);
    const allLines = wrap(ctx, `„${vibe.text}“`, W - 260);
    const lines = allLines.slice(0, Math.max(2, Math.min(4, room)));
    if (lines.length < allLines.length) lines[lines.length - 1] = `${lines[lines.length - 1].replace(/[\s,.–-]+$/, "")} …“`;
    const boxH = lines.length * 56 + 80;
    y += 20;
    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    roundRect(ctx, 90, y, W - 180, boxH, 40);
    ctx.fill();
    ctx.fillStyle = COLORS.text;
    lines.forEach((line, i) => ctx.fillText(line, W / 2, y + 70 + i * 56));
    y += boxH + 80;

    // Unten ist der Button – was nicht mehr passt, wird weggelassen statt zu überlappen
    const bottom = H - 290;

    // Farbtupfer
    if (vibe.colors && vibe.colors.length && y + 110 <= bottom) {
      const gap = 190;
      let x = W / 2 - ((vibe.colors.length - 1) * gap) / 2;
      for (const color of vibe.colors) {
        ctx.beginPath();
        ctx.arc(x, y, 48, 0, Math.PI * 2);
        ctx.fillStyle = color.hex;
        ctx.fill();
        ctx.lineWidth = 6;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
        ctx.font = `600 32px ${SANS}`;
        ctx.fillStyle = COLORS.muted;
        ctx.fillText(color.name, x, y + 95);
        x += gap;
      }
      y += 160;
    }

    // Top-Begriffe als #Hashtags
    if (vibe.terms && vibe.terms.length && y <= bottom + 30) {
      ctx.font = `600 38px ${SANS}`;
      ctx.fillStyle = COLORS.accent;
      ctx.fillText(vibe.terms.map((t) => `#${t.replace(/\s+/g, "")}`).join("  "), W / 2, y);
    }

    // Fuß: Einladung
    ctx.fillStyle = COLORS.accent;
    roundRect(ctx, 140, H - 230, W - 280, 110, 55);
    ctx.fill();
    ctx.font = `700 42px ${SANS}`;
    ctx.fillStyle = "#ffffff";
    ctx.fillText(`Finde deinen Vibe → ${SITE}`, W / 2, H - 160);

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
    overlay.setAttribute("aria-label", "Deine Vibe-Karte");
    const box = document.createElement("div");
    box.className = "vibecard-box";
    const img = Object.assign(document.createElement("img"), {
      src: URL.createObjectURL(blob),
      alt: `Vibe-Karte: ${vibe.emoji} ${vibe.title}`,
      className: "vibecard-image",
    });
    const actions = document.createElement("div");
    actions.className = "vibecard-actions";

    const share = Object.assign(document.createElement("button"), {
      className: "button", textContent: canShare ? "📲 Teilen" : "⬇️ Bild speichern",
    });
    share.addEventListener("click", async () => {
      if (!canShare) return download(blob, filename);
      try {
        await navigator.share({
          files: [file],
          title: "Mein Malipin-Vibe",
          text: `Mein Pinterest-Vibe: ${vibe.emoji} ${vibe.title} – finde deinen auf ${SITE}`,
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
