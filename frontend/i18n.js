// Sprache der App: Deutsch oder Englisch (Wörterbuch: /i18n/en.json, geladen als /i18n-en.js).
//
// 1. Sprache wählen: gespeicherte Wahl -> sonst Browsersprache (Deutsch -> de, sonst en)
// 2. Cookie "lang" setzen, damit auch der Server in der richtigen Sprache antwortet
// 3. Englisch: ALLE Texte, die auf der Seite erscheinen, automatisch übersetzen – auch die,
//    die andere Skripte später einfügen (MutationObserver). Nur Sätze mit Zahlen/Namen
//    darin brauchen im Code t("… {n} …", { n }).
//
// Muss im <head> VOR allen anderen Skripten stehen.

(() => {
  const LANGS = ["de", "en"];
  const read = (key) => { try { return localStorage.getItem(key); } catch { return null; } };

  function choose() {
    const saved = read("malipin-lang");
    if (LANGS.includes(saved)) return saved;
    const browser = navigator.languages || [navigator.language || "de"];
    return browser.some((l) => l.toLowerCase().startsWith("de")) ? "de" : "en";
  }

  const lang = choose();
  document.documentElement.lang = lang;
  document.cookie = `lang=${lang}; path=/; max-age=31536000; samesite=lax`;
  const dict = lang === "en" ? (window.MALIPIN_EN || {}) : {};
  const norm = (text) => text.replace(/\s+/g, " ").trim();

  // t("Hallo {name}", { name: "Mali" }) -> "Hi Mali" (Englisch) / "Hallo Mali" (Deutsch)
  function t(text, values = {}) {
    const out = dict[norm(text)] ?? text;
    return out.replace(/\{(\w+)\}/g, (all, key) => (key in values ? values[key] : all));
  }

  window.t = t;
  window.LANG = lang;
  window.LOCALE = lang === "en" ? "en-GB" : "de-AT";   // Zahlen & Preise
  window.setLanguage = (next) => {
    try { localStorage.setItem("malipin-lang", next); } catch { /* privat: nur Cookie */ }
    document.cookie = `lang=${next}; path=/; max-age=31536000; samesite=lax`;
    location.reload();
  };

  // Sprachumschalter: oben in der Kopfzeile (am Handy ausgeblendet, zu eng) und unten im Footer
  document.addEventListener("DOMContentLoaded", () => {
    const other = lang === "de" ? "en" : "de";
    const makeLink = (className, text) => {
      const link = Object.assign(document.createElement("a"), { href: "#", className, lang: other, textContent: text });
      link.setAttribute("aria-label", other === "en" ? "English" : "Deutsch");
      link.dataset.noI18n = "";
      link.addEventListener("click", (event) => { event.preventDefault(); window.setLanguage(other); });
      return link;
    };
    const nav = document.querySelector(".header-nav");
    if (nav && !nav.querySelector(".lang-switch")) {
      nav.prepend(makeLink("header-link lang-switch", other.toUpperCase()));
    }
    const footer = document.querySelector(".site-footer") || document.querySelector("main");
    if (footer && !footer.querySelector(".lang-switch")) {
      const line = Object.assign(document.createElement("p"), { className: "footer-lang" });
      line.append(makeLink("lang-switch", other === "en" ? "English" : "Deutsch"));
      footer.append(line);
    }
  });

  if (lang !== "en") return;

  // --- Automatisch übersetzen ------------------------------------------------------------------
  const ATTRS = ["aria-label", "title", "placeholder", "alt"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE"]);
  const skipped = (el) => !el || SKIP.has(el.tagName) || el.closest("[data-no-i18n]");

  function textNode(node) {
    if (skipped(node.parentElement)) return;
    const key = norm(node.nodeValue);
    if (key && dict[key] !== undefined && dict[key] !== key) {
      const lead = node.nodeValue.match(/^\s*/)[0];
      const trail = node.nodeValue.match(/\s*$/)[0];
      node.nodeValue = lead + dict[key] + trail;
    }
  }

  function element(el) {
    if (skipped(el)) return;
    for (const name of ATTRS) {
      const value = el.getAttribute(name);
      const translated = value && dict[norm(value)];
      // Nur bei echter Änderung setzen – sonst löst jedes Setzen eine neue Änderung aus (Endlosschleife)
      if (translated && translated !== value) el.setAttribute(name, translated);
    }
  }

  function walk(root) {
    if (root.nodeType === Node.TEXT_NODE) return textNode(root);
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    element(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.TEXT_NODE) textNode(node); else element(node);
    }
  }

  new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === "childList") change.addedNodes.forEach(walk);
      else if (change.type === "characterData") textNode(change.target);
      else element(change.target);
    }
  }).observe(document.documentElement, {
    childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS,
  });
  document.addEventListener("DOMContentLoaded", () => walk(document.documentElement));
})();
