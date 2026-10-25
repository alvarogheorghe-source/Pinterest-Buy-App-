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
