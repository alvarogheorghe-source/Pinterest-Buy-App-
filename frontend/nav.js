// Kopfzeile: Anzahl der gemerkten Teile neben "♡ Merkliste" anzeigen.
// Wird auf jeder Seite geladen und aktualisiert sich, sobald etwas gemerkt wird
// (feedback.js meldet das mit dem Ereignis "merkliste:changed").

async function updateSavedCount() {
  const counters = document.querySelectorAll(".saved-count");
  if (!counters.length) return;
  try {
    const votes = await fetch("/api/feedback").then((r) => r.json());
    const count = Object.values(votes).filter((entry) => entry.vote === "like").length;
    for (const counter of counters) counter.textContent = count ? String(count) : "";
  } catch {
    // Zähler ist nur Deko – bei einem Fehler einfach leer lassen
  }
}

window.addEventListener("merkliste:changed", updateSavedCount);
updateSavedCount();


// "Mit Pinterest verbinden" -> "Pinterest bald verfügbar", solange der Server Pinterest
// noch nicht für alle freigibt (/api/features, PINTEREST_OPEN=0). Gilt auch für Buttons,
// die andere Skripte später einfügen (z.B. im Shop).
(async () => {
  let open = true;
  try { open = (await fetch("/api/features").then((r) => r.json())).pinterest; } catch { return; }
  if (open) return;
  const SELECTOR = ".connect, a[href='/auth/login']";
  const soon = (el) => {
    if (el.classList.contains("soon")) return;
    el.classList.add("soon");
    el.removeAttribute("href");
    el.setAttribute("aria-disabled", "true");
    const icon = el.querySelector("svg");
    el.textContent = t("Pinterest bald verfügbar");
    if (icon) el.prepend(icon);
  };
  const scan = (root) => {
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    if (root.matches(SELECTOR)) soon(root);
    root.querySelectorAll(SELECTOR).forEach(soon);
  };
  scan(document.body);
  // "Kostenlos starten" in der Kopfzeile -> zur Foto-Suche (geht ohne Pinterest)
  document.querySelectorAll(".site-header a[href='/konto.html'].button").forEach((a) => {
    a.href = "/foto.html";
    a.textContent = t("Fit per Foto finden");
  });
  new MutationObserver((changes) => changes.forEach((c) => c.addedNodes.forEach(scan)))
    .observe(document.body, { childList: true, subtree: true });
})();


// Aktuelle Seite in der Kopfzeile hervorheben ("Shop" im Shop, "Stile" im Stil-Lexikon …)
for (const link of document.querySelectorAll(".header-nav a[href^='/']")) {
  if (new URL(link.href).pathname === location.pathname) {
    link.classList.add("is-active");
    link.setAttribute("aria-current", "page");
  }
}
