// Ein Bild teilen 📸 – Vorschau mit "Teilen" (Handy: Instagram, WhatsApp …) bzw. "Bild speichern".
// Gemeinsam für die Vibe-Karte (vibecard.js) und Malis Foto-Fund (fitcard.js).
// Das Bild entsteht im Browser und wird nicht hochgeladen.

(() => {
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

  // canvas -> Vorschau-Fenster. title/text gehen an das Teilen-Menü des Handys.
  async function shareImage(canvas, { filename, title, text, alt }) {
    const blob = await toBlob(canvas);
    const file = new File([blob], filename, { type: "image/png" });
    const canShare = Boolean(navigator.canShare && navigator.canShare({ files: [file] }));

    const overlay = document.createElement("div");
    overlay.className = "vibecard-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-label", alt);
    const box = document.createElement("div");
    box.className = "vibecard-box";
    const img = Object.assign(document.createElement("img"), {
      src: URL.createObjectURL(blob), alt, className: "vibecard-image",
    });
    const actions = document.createElement("div");
    actions.className = "vibecard-actions";

    const share = Object.assign(document.createElement("button"), {
      className: "button", textContent: canShare ? "Teilen" : "Bild speichern",
    });
    share.addEventListener("click", async () => {
      if (!canShare) return download(blob, filename);
      try {
        await navigator.share({ files: [file], title, text });
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

  window.shareImage = shareImage;
})();
