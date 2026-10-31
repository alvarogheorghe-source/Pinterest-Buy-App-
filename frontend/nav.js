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
    if (el.classList.contains("soon") || el.dataset.photo) return;
    // Große Haupt-Buttons (Startseite) nicht tot stehen lassen: dort geht's zur Foto-Suche,
    // die ohne Pinterest funktioniert. Kleine Buttons sagen "bald verfügbar".
    if (el.classList.contains("large") || el.closest(".mobile-cta")) {
      el.dataset.photo = "1";
      el.classList.remove("connect");
      el.href = "/foto.html";
      el.innerHTML = '<svg class="icon"><use href="#i-camera"/></svg>';
      el.append(t("Fit per Foto finden"));
      return;
    }
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
  // Zweiter Button, der ohne Pinterest woanders hinführen soll (data-closed-href/-text)
  document.querySelectorAll("[data-closed-href]").forEach((a) => {
    a.href = a.dataset.closedHref;
    a.textContent = t(a.dataset.closedText);
  });
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


// Besucherzählung ohne Cookies (backend/stats.py): nur "Seite aufgerufen" und "zu einem Shop
// geklickt", keine Kennung, nichts im Browser gespeichert.
function hit(data) {
  const body = new Blob([JSON.stringify(data)], { type: "application/json" });
  if (!navigator.sendBeacon?.("/api/hit", body)) {
    fetch("/api/hit", { method: "POST", body, keepalive: true }).catch(() => {});
  }
}

// Woher? ?von=tiktok (Bio-Link) bzw. utm_source, sonst die verweisende Seite. Danach den
// Zusatz aus der Adresse nehmen, damit er beim Weiterteilen nicht mitwandert.
(() => {
  const params = new URLSearchParams(location.search);
  const source = params.get("von") || params.get("utm_source") || params.get("ref") || "";
  hit({ type: "view", page: location.pathname, source, referrer: document.referrer });
  if (source) {
    // Kommt über einen Werbe-/Bio-Link: keine lange Begrüßung, gleich die Seite (bunny.js)
    document.documentElement.dataset.fromLink = "1";
    ["von", "utm_source", "utm_medium", "utm_campaign", "ref"].forEach((key) => params.delete(key));
    const rest = params.toString();
    history.replaceState(null, "", location.pathname + (rest ? `?${rest}` : "") + location.hash);
  }
})();
document.addEventListener("click", (event) => {
  const link = event.target.closest?.("a[href^='http']");
  if (link && link.host !== location.host) hit({ type: "click", url: link.href });
}, true);


// Second Hand: Such-Knöpfe zu Vinted/willhaben (backend/secondhand.py). Normale Links ohne
// Provision -> keine "Werbung"-Kennzeichnung. Gibt null zurück, wenn es keine gibt.
function secondhandLinks(links, label = "Second Hand suchen:") {
  if (!links?.length) return null;
  const row = document.createElement("p");
  row.className = "secondhand-links";
  row.append(Object.assign(document.createElement("span"), { textContent: t(label) }));
  for (const link of links) {
    row.append(Object.assign(document.createElement("a"), {
      className: "chip", href: link.url, target: "_blank", rel: "noopener", textContent: link.name,
    }));
  }
  return row;
}
