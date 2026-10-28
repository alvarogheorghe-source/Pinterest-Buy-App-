// Mali arbeitet 🥕 – Ansicht für die Hintergrund-Analyse (backend/analysis.py).
//
// Nach "Pins laden" schaut sich Mali die Pins automatisch an. Diese Ansicht zeigt dabei:
// Mali, der eine Karotte knabbert, eine Sprechblase mit wechselnden Sätzen, einen
// Fortschrittsbalken und die Schritte. Man kann sie verkleinern (dann bleibt unten ein
// kleiner Knopf "Mali arbeitet … 40 %") und einfach weitersurfen.
// Ist Mali fertig, meldet die Seite "analysis:done" (der Shop lädt dann neu).

(() => {
  if (document.body.hasAttribute("data-static")) return; // Vorstellungsseite: kein Server

  const STEPS = [
    { key: "farben", label: "Farben erkennen", weight: 10 },
    { key: "vorbereiten", label: "Mali wird wach", weight: 15 },
    { key: "bilder", label: "Bilder ansehen", weight: 55 },
    { key: "stil", label: "Stil, Teile & Marken", weight: 15 },
    { key: "schwerpunkte", label: "Stil-Landkarte", weight: 5 },
  ];
  const TALK = {
    farben: ["Ich misch gerade meine Farbpalette … 🎨", "Beige? Schwarz? Ich schau ganz genau hin!"],
    vorbereiten: ["Moment, ich putz kurz meine Pixel-Brille … 👓",
      "Beim ersten Mal brauch ich etwas länger zum Aufwachen. 😴"],
    bilder: ["Ich schau mir jedes Bild ganz genau an. 👀", "Oh, das gefällt mir! Weiter geht's …",
      "Karottenpause? Nein, weiterarbeiten! 🥕", "Du hast echt einen guten Geschmack, weißt du das?",
      "Ich merk mir alles – Schnitte, Farben, Sneaker …"],
    stil: ["Jetzt sortiere ich: Stil, Teile, Marken … 🗂️", "Hmm, ich glaub, ich kenn deinen Vibe schon …"],
    schwerpunkte: ["Fast fertig – ich bau dir deine Stil-Landkarte! 🗺️"],
  };
  const POLL_MS = 1000;
  const TALK_MS = 3400;

  // --- Aufbau ----------------------------------------------------------------------------------

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };

  const panel = el("section", "analysis");
  panel.setAttribute("aria-label", "Mali analysiert deine Pins");
  panel.hidden = true;
  const close = el("button", "analysis-minimize", "–");
  close.setAttribute("aria-label", "Verkleinern");
  const title = el("h2", "analysis-title", "Mali schaut sich deine Pins an");
  const stage = el("div", "analysis-stage");
  const sprite = el("canvas", "analysis-sprite");
  const bubble = el("p", "analysis-bubble");
  bubble.setAttribute("aria-live", "polite");
  stage.append(sprite, bubble);
  const bar = el("div", "analysis-bar");
  bar.setAttribute("role", "progressbar");
  bar.setAttribute("aria-valuemin", "0");
  bar.setAttribute("aria-valuemax", "100");
  const fill = el("span");
  bar.appendChild(fill);
  const count = el("p", "analysis-count");
  const steps = el("ol", "analysis-steps");
  const stepItems = STEPS.map((step) => {
    const li = el("li", "", step.label);
    steps.appendChild(li);
    return li;
  });
  const found = el("div", "analysis-found");
  const actions = el("div", "analysis-actions");
  panel.append(close, title, stage, bar, count, steps, found, actions);

  const pill = el("button", "analysis-pill");
  pill.hidden = true;
  document.body.append(panel, pill);

  // --- Mali zeichnen ---------------------------------------------------------------------------

  function draw(frameName) {
    const pixels = window.mali && window.mali.pixels;
    if (!pixels) return;
    const grid = pixels.frames[frameName];
    sprite.width = grid[0].length;
    sprite.height = grid.length;
    const ctx = sprite.getContext("2d");
    ctx.clearRect(0, 0, sprite.width, sprite.height);
    grid.forEach((row, y) => row.forEach((cell, x) => {
      if (cell === ".") return;
      ctx.fillStyle = pixels.palette[cell];
      ctx.fillRect(x, y, 1, 1);
    }));
  }

  // --- Anzeige aktualisieren -------------------------------------------------------------------

  let state = null;
  let talkIndex = 0;
  let lastStep = null;
  let chewing = false;
  let autoHide = null;                  // Fertig-Fenster im Shop schließt sich nach ein paar Sekunden
  const AUTO_HIDE_MS = 6000;
  let timers = [];

  function percent(s) {
    if (s.status === "done") return 100;
    let total = 0;
    for (const step of STEPS) {
      if (step.key === s.step) {
        const part = s.total ? Math.min(1, s.done / s.total) : 0.3;
        return Math.round(total + step.weight * part);
      }
      total += step.weight;
    }
    return 0;
  }

  function say(text) {
    if (bubble.textContent === text) return;
    bubble.classList.remove("pop");
    void bubble.offsetWidth; // Animation neu starten
    bubble.textContent = text;
    bubble.classList.add("pop");
  }

  function talk() {
    if (!state || state.status !== "running") return;
    const lines = TALK[state.step] || TALK.bilder;
    // Ab und zu den echten Fortschritt erwähnen
    if (state.step === "bilder" && state.total && talkIndex % 3 === 2) {
      say(t("Schon {done} von {total} Bildern – läuft! 🏃", { done: state.done, total: state.total }));
    } else {
      say(lines[talkIndex % lines.length]);
    }
    talkIndex += 1;
  }

  function render() {
    const s = state;
    const pct = percent(s);
    fill.style.width = `${pct}%`;
    bar.setAttribute("aria-valuenow", String(pct));
    const current = STEPS.findIndex((step) => step.key === s.step);
    stepItems.forEach((li, i) => {
      li.className = s.status === "done" || i < current ? "done" : i === current ? "active" : "";
    });
    count.textContent = s.status === "running" && s.step === "bilder" && s.total
      ? t("{done} von {total} Bildern", { done: s.done, total: s.total }) : "";
    pill.textContent = s.status === "running" ? t("🥕 Mali arbeitet … {pct} %", { pct })
      : "🥕 Mali ist fertig!";

    actions.replaceChildren();
    found.replaceChildren();
    if (s.status === "done") {
      chewing = false;
      draw("happy");
      title.textContent = "Fertig! 🎉";
      if (s.vision === false) {
        say("Fertig! Ohne Bilderkennung hab ich mir Farben und Texte angeschaut.");
      } else if (s.found && s.found.length) {
        say(t("Ich hab dich durchschaut: {terms} … 😏", { terms: s.found.slice(0, 3).map((x) => t(x)).join(", ") }));
        for (const term of s.found) found.appendChild(el("span", "chip", term));
      } else {
        say("Fertig! Deine Pins sind jetzt in meinem Hasen-Gedächtnis. 🥕");
      }
      if (location.pathname === "/shop.html") {
        const look = el("button", "button", "Ergebnisse ansehen");
        look.addEventListener("click", hide);
        actions.append(look);
        if (!autoHide) autoHide = setTimeout(hide, AUTO_HIDE_MS);   // nicht über den Produkten stehen bleiben
      } else {
        const shop = Object.assign(el("a", "button", "Zum Shop"), { href: "/shop.html" });
        const ok = el("button", "button secondary", "Schließen");
        ok.addEventListener("click", hide);
        actions.append(shop, ok);
      }
    } else if (s.status === "error") {
      chewing = false;
      draw("idle");
      title.textContent = "Hoppla!";
      say("Da hat was nicht geklappt. Ich versuch's gern nochmal! 🥕");
      const retry = el("button", "button", "Nochmal versuchen");
      retry.addEventListener("click", () => start());
      const ok = el("button", "button secondary", "Schließen");
      ok.addEventListener("click", hide);
      actions.append(retry, ok);
    } else {
      title.textContent = "Mali schaut sich deine Pins an";
      if (!chewing) { chewing = true; chew(); }
      // Neuer Schritt -> Mali sagt sofort etwas Passendes (nicht erst beim nächsten Wechsel)
      if (s.step !== lastStep) {
        lastStep = s.step;
        talkIndex = 0;
        talk();
      }
    }
  }

  // Karotte knabbern, solange gearbeitet wird
  function chew() {
    if (!chewing) return;
    draw(Math.floor(Date.now() / 420) % 2 ? "eat1" : "eat2");
    timers.push(setTimeout(chew, 420));
  }

  // --- Abfragen ----------------------------------------------------------------------------------

  async function poll() {
    try {
      state = await fetch("/api/analysis").then((r) => r.json());
    } catch {
      timers.push(setTimeout(poll, POLL_MS * 3));
      return;
    }
    render();
    if (state.status === "running") {
      timers.push(setTimeout(poll, POLL_MS));
    } else {
      window.dispatchEvent(new CustomEvent("analysis:done", { detail: state }));
    }
  }

  function show() {
    panel.hidden = false;
    pill.hidden = true;
    document.body.classList.add("analysis-open");
  }

  function hide() {
    panel.hidden = true;
    pill.hidden = true;
    document.body.classList.remove("analysis-open");
    chewing = false;
    timers.forEach(clearTimeout);
    timers = [];
  }

  function minimize() {
    panel.hidden = true;
    pill.hidden = false;
    document.body.classList.remove("analysis-open");
  }

  async function start() {
    state = await fetch("/api/analysis", { method: "POST" }).then((r) => r.json());
    open();
  }

  function open() {
    timers.forEach(clearTimeout);       // nie doppelt pollen/reden
    timers = [];
    show();
    talkIndex = 0;
    render();
    talk();
    timers.push(setInterval(talk, TALK_MS));
    poll();
  }

  close.addEventListener("click", minimize);
  pill.addEventListener("click", () => (state && state.status !== "running" ? hide() : show()));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) minimize();
  });

  // Beim Laden der Seite: Läuft Mali schon, oder gibt es neue Pins zum Anschauen?
  window.addEventListener("load", async () => {
    try {
      state = await fetch("/api/analysis").then((r) => r.json());
    } catch {
      return;
    }
    if (state.status === "running") open();
    else if (state.needed) start();
  });

  // Für konto.js: nach "Pins laden" (der Server hat die Analyse schon gestartet)
  window.maliAnalysis = { open, start };
})();
