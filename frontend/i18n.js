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
  // Land & Währung: nur eine bewusste Wahl wird gespeichert – sonst entscheidet der Server
  // (Browsersprache "en-US" -> USA, Hosting-Ländercode …), siehe backend/region.py
  const country = read("malipin-country");
  if (country) document.cookie = `country=${country}; path=/; max-age=31536000; samesite=lax`;
  const dict = lang === "en" ? (window.MALIPIN_EN || {}) : {};
  const norm = (text) => text.replace(/\s+/g, " ").trim();

  // t("Hallo {name}", { name: "Mali" }) -> "Hi Mali" (Englisch) / "Hallo Mali" (Deutsch)
  function t(text, values = {}) {
    const out = dict[norm(text)] ?? text;
    return out.replace(/\{(\w+)\}/g, (all, key) => (key in values ? values[key] : all));
  }

  // Preis eines Produkts in der Währung der Person (Server rechnet um: local_price/local_currency).
  // Umgerechnet -> "≈ 27,40 $", sonst der Originalpreis.
  function money(item) {
    const amount = item.local_price ?? item.price;
    const currency = item.local_currency ?? item.currency ?? "EUR";
    const text = new Intl.NumberFormat(window.LOCALE, { style: "currency", currency }).format(amount);
    return item.converted ? `≈ ${text}` : text;
  }

  // Sale: Rabatt in Prozent und der alte Preis ("statt 49,90 €") – oder null
  function sale(item) {
    const now = item.local_price ?? item.price;
    const before = item.local_original_price ?? item.original_price;
    if (!before || !now || before <= now) return null;
    const currency = item.local_currency ?? item.currency ?? "EUR";
    return {
      percent: Math.round((1 - now / before) * 100),
      before: new Intl.NumberFormat(window.LOCALE, { style: "currency", currency }).format(before),
    };
  }

  window.t = t;
  window.money = money;
  window.sale = sale;
  window.LANG = lang;
  // Zahlen & Preise im Format des eigenen Browsers ("$70.19" in den USA, "£55.24" in UK),
  // solange dessen Sprache zur gewählten passt – sonst Standard
  const browserLocale = (navigator.languages || [navigator.language || ""])
    .find((l) => l.toLowerCase().startsWith(lang) && l.includes("-"));
  window.LOCALE = browserLocale || (lang === "en" ? "en-GB" : "de-AT");
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
      (nav.querySelector(".nav-icons") || nav).append(makeLink("lang-switch lang-pill", other.toUpperCase()));
    }
    const footer = document.querySelector(".site-footer") || document.querySelector("main");
    if (footer && !footer.querySelector(".lang-switch")) {
      const line = Object.assign(document.createElement("p"), { className: "footer-lang" });
      line.append(makeLink("lang-switch", other === "en" ? "English" : "Deutsch"));
      footer.append(line);
      addCountryChoice(line);
    }
  });

  // Land wählen (Footer): "Österreich · EUR" – Wechsel lädt die Seite neu
  async function addCountryChoice(line) {
    let data;
    try { data = await fetch("/api/region").then((r) => r.json()); } catch { return; }
    const select = Object.assign(document.createElement("select"), { className: "country-select" });
    select.setAttribute("aria-label", lang === "en" ? "Country" : "Land");
    select.dataset.noI18n = "";
    for (const c of data.countries) {
      select.append(Object.assign(document.createElement("option"),
        { value: c.code, textContent: `${c.name} · ${c.currency}`, selected: c.code === data.country }));
    }
    select.addEventListener("change", () => {
      try { localStorage.setItem("malipin-country", select.value); } catch { /* nur Cookie */ }
      document.cookie = `country=${select.value}; path=/; max-age=31536000; samesite=lax`;
      location.reload();
    });
    window.CURRENCY = data.currency;
    line.append(" · ", select);
    // Beispielpreise (Startseite) mit dem Währungszeichen der Person: "$34.99", "£34.99" …
    // (gleiche Zahl – es sind nur Beispiele, keine echten Angebote)
    for (const el of document.querySelectorAll("[data-price]")) {
      el.textContent = new Intl.NumberFormat(window.LOCALE, { style: "currency", currency: data.currency })
        .format(Number(el.dataset.price));
    }
  }

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
