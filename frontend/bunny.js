// Mali – das Pixel-Maskottchen von Malipin 🐰
//
// Mali läuft unten über jede Seite, isst Karotten, schläft, tanzt, folgt dir
// manchmal, stellt beim ersten Besuch die Website vor, freut sich über 👍 und
// verrät dir per Klick, welchen Vibe dein Pinterest abgibt (/api/vibe).
//
// Wird auf JEDER Seite geladen (nach den anderen Skripten). Aussehen: bunny.css

(() => {
  const NAME = "Mali";

  // --- 1. Pixel-Zeichnung ------------------------------------------------------------------
  // Jede Figur ist ein Raster aus Buchstaben (16 × 16). Jeder Buchstabe = ein Pixel
  // in der Farbe aus PALETTE, "." = durchsichtig. Zum Umzeichnen einfach Buchstaben ändern!

  const PALETTE = {
    o: "#6b5656", // Umriss
    w: "#fffaf6", // Fell
    s: "#f1e1da", // Fell-Schatten
    p: "#f6a5b9", // rosa (Ohren innen, Nase, Pfoten)
    b: "#ffc7d1", // Bäckchen
    k: "#2d2326", // Augen
    c: "#f2873a", // Karotte
    g: "#68b85a", // Karottengrün
    r: "#ff6b8b", // Herz
  };

  const IDLE = [
    "....oo....oo....",
    "...owwo..owwo...",
    "...owpo..opwo...",
    "...owpo..opwo...",
    "...owpo..opwo...",
    "...owwoooowwo...",
    "..owwwwwwwwwwo..",
    ".owwwwwwwwwwwwo.",
    ".owwkkwwwwkkwwo.",
    ".owbkkwwwwkkbwo.",
    ".owwwwwppwwwwwo.",
    "..owwwwwwwwwwo..",
    "..owwwwwwwwwwo..",
    ".oswwwwwwwwwwso.",
    ".oswpwwwwwwpwso.",
    "..oooooooooooo..",
  ];

  // Varianten: nur die Zeilen, die sich vom IDLE-Bild unterscheiden
  const EYES_CLOSED = { 8: ".owwwwwwwwwwwwo.", 9: ".owboowwwwoobwo." };
  const EYES_HAPPY = { 8: ".owwwowwwwowwwo.", 9: ".owbowowwowobwo." };

  // Karotte: [Zeile, Spalte, Farbe] – wird über das Bild gemalt
  const CARROT_FULL = [[10, 13, "g"], [10, 14, "g"], [11, 13, "g"],
    [11, 8, "c"], [11, 9, "c"], [11, 10, "c"], [11, 11, "c"], [11, 12, "c"],
    [12, 10, "c"], [12, 11, "c"], [12, 12, "c"]];
  const CARROT_BITTEN = [[10, 13, "g"], [10, 14, "g"], [11, 13, "g"],
    [11, 10, "c"], [11, 11, "c"], [11, 12, "c"], [12, 11, "c"], [12, 12, "c"],
    [13, 7, "c"]]; // ein Krümel

  function frame(changedRows = {}, overlay = []) {
    const rows = IDLE.map((row, i) => changedRows[i] || row);
    const grid = rows.map((row) => row.split(""));
    for (const [r, c, color] of overlay) grid[r][c] = color;
    return grid;
  }

  const FRAMES = {
    idle: frame(),
    blink: frame(EYES_CLOSED),
    happy: frame(EYES_HAPPY),
    eat1: frame({}, CARROT_FULL),
    eat2: frame(EYES_CLOSED, CARROT_BITTEN),
  };

  const HEART = [".rr.rr.", "rrrrrrr", "rrrrrrr", ".rrrrr.", "..rrr..", "...r..."]
    .map((row) => row.split(""));

  function draw(canvas, grid) {
    canvas.width = grid[0].length;
    canvas.height = grid.length;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    grid.forEach((row, y) => row.forEach((cell, x) => {
      if (cell === ".") return;
      ctx.fillStyle = PALETTE[cell];
      ctx.fillRect(x, y, 1, 1);
    }));
  }

  // --- Hilfen ---------------------------------------------------------------------------------

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const random = (min, max) => min + Math.random() * (max - min);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Speicher im Browser – kann blockiert sein (privates Fenster), daher immer mit try
  function remember(store, key, value) {
    try { store.setItem(key, value); } catch { /* egal */ }
  }
  function recall(store, key) {
    try { return store.getItem(key); } catch { return null; }
  }

  // --- 2. Mali auf die Seite setzen ---------------------------------------------------------

  const el = document.createElement("div");
  el.className = "mali";
  el.setAttribute("role", "button");
  el.tabIndex = 0;
  el.setAttribute("aria-label", `${NAME} – klick mich für deinen Pinterest-Vibe`);
  const body = document.createElement("div");
  body.className = "mali-body";
  const sprite = document.createElement("canvas");
  sprite.className = "mali-sprite";
  body.appendChild(sprite);
  el.appendChild(body);

  const bubble = document.createElement("div");
  bubble.className = "mali-bubble";
  bubble.setAttribute("role", "status");
  bubble.setAttribute("aria-live", "polite");
  bubble.hidden = true;

  const returnButton = document.createElement("button");
  returnButton.className = "mali-return";
  returnButton.textContent = "🐾";
  returnButton.setAttribute("aria-label", `${NAME} zurückholen`);
  returnButton.hidden = true;

  document.body.append(el, bubble, returnButton);

  let currentFrame = "idle";
  function show(name) {
    currentFrame = name;
    draw(sprite, FRAMES[name]);
  }
  show("idle");

  // Position (x = Abstand vom linken Rand) – über Seiten hinweg gemerkt
  const width = () => el.offsetWidth || 64;
  const maxX = () => Math.max(8, window.innerWidth - width() - 8);
  let x = Number(recall(sessionStorage, "mali-x"));
  if (!Number.isFinite(x) || x <= 0) x = random(8, maxX());
  x = Math.min(x, maxX());
  el.style.left = `${x}px`;

  function setX(newX) {
    x = Math.max(8, Math.min(newX, maxX()));
    el.style.left = `${x}px`;
    remember(sessionStorage, "mali-x", String(Math.round(x)));
  }

  window.addEventListener("resize", () => setX(x));

  // --- Bewegungen -------------------------------------------------------------------------------

  let busy = false; // macht Mali gerade etwas?

  // Kleiner Effekt über dem Kopf (Herz, z, ♪), der hochschwebt und verschwindet
  function effect(content) {
    const fx = document.createElement("div");
    fx.className = "mali-fx";
    if (content === "heart") {
      const heart = document.createElement("canvas");
      draw(heart, HEART);
      fx.appendChild(heart);
    } else {
      fx.textContent = content;
    }
    fx.style.left = `${random(10, 40)}px`;
    el.appendChild(fx);
    setTimeout(() => fx.remove(), 1400);
  }

  async function hopTo(targetX) {
    targetX = Math.max(8, Math.min(targetX, maxX()));
    const distance = Math.abs(targetX - x);
    if (distance < 10) return;
    if (reduceMotion) { setX(targetX); return; }
    const duration = Math.max(400, distance * 6); // ca. 6 ms pro Pixel
    el.classList.toggle("facing-left", targetX < x);
    el.style.transition = `left ${duration}ms linear`;
    el.classList.add("hopping");
    setX(targetX);
    await wait(duration);
    el.classList.remove("hopping");
    el.style.transition = "";
  }

  // Sofort anhalten (z.B. wenn man auf Mali klickt, während er hoppelt)
  function stop() {
    const current = el.getBoundingClientRect().left;
    el.style.transition = "";
    el.classList.remove("hopping", "dancing");
    setX(current);
  }

  async function blink() {
    if (currentFrame !== "idle") return;
    show("blink");
    await wait(160);
    if (currentFrame === "blink") show("idle");
  }

  async function eatCarrot() {
    for (let i = 0; i < 10; i++) {
      show(i % 2 ? "eat2" : "eat1");
      await wait(260);
    }
    show("happy");
    if (Math.random() < 0.4) say([pick(["Mmmh 🥕", "Karotten-Pause!", "Nom nom nom"])], { autoClose: 1800 });
    await wait(700);
    show("idle");
  }

  async function nap() {
    show("blink");
    for (let i = 0; i < 5; i++) {
      effect("z");
      await wait(900);
    }
    show("idle");
  }

  async function dance() {
    if (reduceMotion) return;
    el.classList.add("dancing");
    show("happy");
    for (let i = 0; i < 4; i++) {
      effect(pick(["♪", "♫"]));
      await wait(600);
    }
    el.classList.remove("dancing");
    show("idle");
  }

  async function happyJump() {
    show("happy");
    effect("heart");
    if (!reduceMotion) {
      el.classList.add("jumping");
      await wait(600);
      el.classList.remove("jumping");
    }
    effect("heart");
    await wait(500);
    show("idle");
  }

  // Maus merken – manchmal hoppelt Mali zu dir
  let mouse = null;
  window.addEventListener("mousemove", (event) => { mouse = { x: event.clientX, at: Date.now() }; });

  // --- 3. Sprechblase -------------------------------------------------------------------------

  // parts: Liste aus Text oder fertigen Elementen. buttons: [{text, onClick, primary}]
  function say(parts, { buttons = [], autoClose = 0 } = {}) {
    bubble.replaceChildren();
    for (const part of parts) {
      bubble.appendChild(typeof part === "string" ? Object.assign(document.createElement("p"),
        { textContent: part }) : part);
    }
    if (buttons.length) {
      const row = document.createElement("div");
      row.className = "mali-buttons";
      for (const { text, onClick, primary } of buttons) {
        const button = document.createElement("button");
        button.textContent = text;
        if (primary) button.className = "primary";
        button.addEventListener("click", (event) => { event.stopPropagation(); onClick(); });
        row.appendChild(button);
      }
      bubble.appendChild(row);
    }
    const close = document.createElement("button");
    close.className = "mali-close";
    close.textContent = "×";
    close.setAttribute("aria-label", "Sprechblase schließen");
    close.addEventListener("click", () => hideBubble());
    bubble.appendChild(close);

    bubble.hidden = false;
    placeBubble();
    clearTimeout(say.timer);
    if (autoClose) say.timer = setTimeout(hideBubble, autoClose);
  }

  function hideBubble() {
    bubble.hidden = true;
    clearTimeout(say.timer);
  }

  // Blase über Mali, aber nie über den Bildschirmrand hinaus
  function placeBubble() {
    const rect = el.getBoundingClientRect();
    const bubbleWidth = bubble.offsetWidth;
    const center = rect.left + rect.width / 2;
    const left = Math.max(8, Math.min(center - bubbleWidth / 2, window.innerWidth - bubbleWidth - 8));
    bubble.style.left = `${left}px`;
    bubble.style.bottom = `${window.innerHeight - rect.top + 10}px`;
    bubble.style.setProperty("--tail-x", `${center - left}px`); // Spitze zeigt auf Mali
  }

  window.addEventListener("resize", () => { if (!bubble.hidden) placeBubble(); });

  // --- 4. Begrüßung beim allerersten Besuch der Website ------------------------------------
  // Rosa Bildschirm, großer Mali hüpft herein, Text tippt sich ein, dann fliegt
  // Mali klein an seinen Platz unten. Geht von selbst weg (Antippen überspringt).

  const WELCOME = [
    `Hi, ich bin ${NAME} – klein, flauschig und voller Stil-Ideen! 🐰`,
    "Ich schnupper durch deine Pinterest-Boards und finde Mode & Deko, die zu dir passt. 💕",
    "Und ich pass auf dein Budget auf – Karotten-Ehrenwort! 🥕",
  ];
  const TYPE_SPEED = 30;      // ms pro Buchstabe – ruhig genug zum Mitlesen
  const LINE_PAUSE = 1300;    // Lesezeit nach jeder Zeile ...
  const PAUSE_PER_CHAR = 10;  // ... plus etwas mehr bei langen Sätzen

  async function welcome() {
    // Nur beim allerersten Besuch: localStorage bleibt auch nach dem Schließen des Browsers
    if (el.hidden || recall(localStorage, "mali-welcome") === "done") return;
    remember(localStorage, "mali-welcome", "done");

    // Aufbau: Bildschirm > Bühne > großer Mali, Name, Text
    const overlay = document.createElement("div");
    overlay.className = "mali-splash";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-label", `${NAME} begrüßt dich`);
    const stage = document.createElement("div");
    stage.className = "splash-stage";
    const big = document.createElement("canvas");
    big.className = "splash-sprite";
    draw(big, FRAMES.idle);
    const name = Object.assign(document.createElement("p"), { className: "splash-name", textContent: NAME });
    const line = Object.assign(document.createElement("p"), { className: "splash-text" });
    line.setAttribute("aria-hidden", "true"); // das Tippen ist nur fürs Auge ...
    const spoken = Object.assign(document.createElement("p"),
      { className: "visually-hidden", textContent: WELCOME.join(" ") }); // ... Screenreader lesen alles
    const skipHint = Object.assign(document.createElement("p"),
      { className: "splash-skip", textContent: "Tippen zum Überspringen" });
    stage.append(big, name, line);
    overlay.append(stage, spoken, skipHint);
    document.body.appendChild(overlay);
    document.documentElement.classList.add("splash-open"); // Scrollen kurz sperren
    el.classList.add("waiting");                            // kleiner Mali wartet unsichtbar

    // Überspringen per Klick/Tippen oder Escape
    let skipped = false;
    const listeners = new AbortController();
    const skip = new Promise((resolve) => {
      const onSkip = () => { skipped = true; resolve(); };
      overlay.addEventListener("click", onSkip, { signal: listeners.signal });
      document.addEventListener("keydown", (event) => { if (event.key === "Escape") onSkip(); },
        { signal: listeners.signal });
    });
    const pause = (ms) => Promise.race([wait(ms), skip]); // Warten, aber Überspringen geht vor

    function hearts() {
      for (let i = 0; i < 3; i++) {
        const heart = document.createElement("canvas");
        heart.className = "splash-heart";
        draw(heart, HEART);
        heart.style.left = `${random(15, 75)}%`;
        heart.style.animationDelay = `${i * 180}ms`;
        stage.appendChild(heart);
        setTimeout(() => heart.remove(), 2000);
      }
    }

    await pause(reduceMotion ? 200 : 650); // Zeit für den Hereinhüpfer (CSS)
    for (const [i, text] of WELCOME.entries()) {
      if (skipped) break;
      if (reduceMotion) {
        line.textContent = text;
      } else {
        line.textContent = "";
        for (const char of text) { // for...of zerlegt Emojis nicht in Einzelteile
          if (skipped) break;
          line.textContent += char;
          await pause(TYPE_SPEED);
        }
      }
      if (i === 0) { draw(big, FRAMES.happy); hearts(); }               // Freude!
      if (i === 1) { draw(big, FRAMES.blink); await pause(200); draw(big, FRAMES.idle); } // zwinkern
      if (i === 2) draw(big, FRAMES.eat1);                               // Karotte!
      // ohne Tippen-Animation etwas mehr Lesezeit
      await pause(LINE_PAUSE + text.length * PAUSE_PER_CHAR + (reduceMotion ? 450 : 0));
    }
    listeners.abort();

    // Abgang: großer Mali fliegt an den Platz des kleinen, Hintergrund blendet aus
    overlay.classList.add("leaving");
    if (!reduceMotion && big.animate) {
      const from = big.getBoundingClientRect();
      const to = el.getBoundingClientRect();
      const dx = to.left + to.width / 2 - (from.left + from.width / 2);
      const dy = to.top + to.height / 2 - (from.top + from.height / 2);
      draw(big, FRAMES.idle);
      await big.animate(
        [{ transform: "none" }, { transform: `translate(${dx}px, ${dy}px) scale(${to.width / from.width})` }],
        { duration: 750, easing: "cubic-bezier(0.5, -0.3, 0.4, 1)", fill: "forwards" },
      ).finished;
    } else {
      await wait(400);
    }
    overlay.remove();
    document.documentElement.classList.remove("splash-open");
    el.classList.remove("waiting");
  }

  // --- 5. Vibe-Check beim Klick ---------------------------------------------------------------

  async function showVibe() {
    stop();
    busy = true;
    // Vorstellungsseite (malipin.com, ohne Server): noch kein Vibe-Check möglich
    if (document.body.hasAttribute("data-static")) {
      say(["Bald lese ich deinen Vibe aus deinen Pinterest-Boards – Goth Baddie? Clean Girl? 🔮",
        "Ich hoppel schon los, versprochen! 🥕"], { buttons: [{ text: `${NAME} verstecken`, onClick: hideMali }] });
      await happyJump();
      busy = false;
      return;
    }
    say(["Moment, ich schnupper an deinen Pins … 👃"]);
    let vibe;
    try {
      vibe = await fetch("/api/vibe").then((r) => r.json());
    } catch {
      say(["Hoppla, meine Ohren empfangen gerade nichts. Probier's gleich nochmal! 📡"],
        { autoClose: 3000 });
      busy = false;
      return;
    }

    const title = document.createElement("p");
    title.className = "mali-title";
    title.textContent = `Du bist: ${vibe.emoji} ${vibe.title}`;
    const parts = [title, vibe.text];
    if (vibe.second) parts.push(`… mit einer Prise ${vibe.second}`);
    if (vibe.terms.length) {
      const terms = document.createElement("p");
      terms.className = "mali-terms";
      terms.textContent = `Deine Top-Vibes: ${vibe.terms.join(" · ")}`;
      parts.push(terms);
    }

    const buttons = vibe.pin_count === 0
      ? [{ text: "Pinterest verbinden", primary: true, onClick: () => { location.href = "/konto.html"; } }]
      : [{ text: "Nochmal! 🎲", primary: true, onClick: showVibe }];
    buttons.push({ text: `${NAME} verstecken`, onClick: hideMali });

    say(parts, { buttons });
    await happyJump();
    busy = false;
  }

  el.addEventListener("click", () => showVibe());
  el.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); el.click(); }
  });

  // Ausblenden / zurückholen (gemerkt)
  function hideMali() {
    hideBubble();
    el.hidden = true;
    returnButton.hidden = false;
    remember(localStorage, "mali-hidden", "1");
  }
  returnButton.addEventListener("click", () => {
    el.hidden = false;
    returnButton.hidden = true;
    remember(localStorage, "mali-hidden", "0");
    say(["Da bin ich wieder! 🐰"], { autoClose: 2000 });
    happyJump();
  });
  if (recall(localStorage, "mali-hidden") === "1") {
    el.hidden = true;
    returnButton.hidden = false;
  }

  // Reaktion auf 👍 / 👎 (feedback.js meldet das)
  window.addEventListener("mali:like", () => {
    if (el.hidden) return;
    say([pick(["Gemerkt! 💖", "Ooh, das passt sooo zu dir!", "Gute Wahl – iconic! 💅",
      "Ich hätte es auch gewählt. Ehrlich! 🐰"])], { autoClose: 2200 });
    happyJump();
  });
  window.addEventListener("mali:dislike", () => {
    if (el.hidden) return;
    say([pick(["Verstanden – weg damit! 🫡", "Okay, sowas zeig ich dir seltener.",
      "Nicht dein Vibe? Kein Ding! ✌️"])], { autoClose: 2200 });
  });

  // --- 6. Zufalls-Alltag ----------------------------------------------------------------------

  async function life() {
    busy = true;
    await welcome(); // Begrüßung beim ersten Öffnen (sonst sofort weiter)
    busy = false;
    // Kleiner Auftritt beim Laden der Seite
    if (!reduceMotion && !el.hidden) happyJump();

    setInterval(() => { if (!busy && Math.random() < 0.6) blink(); }, 2500);

    if (reduceMotion) return; // keine Zufallsbewegungen
    for (;;) {
      await wait(random(4000, 9000));
      if (el.hidden || !bubble.hidden || busy || document.hidden) continue;
      busy = true;
      const roll = Math.random();
      if (roll < 0.4) {
        await hopTo(random(8, maxX()));
      } else if (roll < 0.55 && mouse && Date.now() - mouse.at < 3000) {
        await hopTo(mouse.x - width() / 2); // dir hinterher!
      } else if (roll < 0.72) {
        await eatCarrot();
      } else if (roll < 0.84) {
        await dance();
      } else {
        await nap();
      }
      busy = false;
    }
  }

  // Zum Ausprobieren in der Browser-Konsole (Rechtsklick → Untersuchen → Konsole):
  //   mali.tanzen()   mali.essen()   mali.schlafen()   mali.freuen()
  //   mali.hoppeln(300)   mali.vibe()   mali.begruessen()
  window.mali = {
    tanzen: dance, essen: eatCarrot, schlafen: nap, freuen: happyJump,
    hoppeln: (targetX) => hopTo(targetX), vibe: showVibe,
    begruessen: () => { remember(localStorage, "mali-welcome", ""); return welcome(); },
  };

  life();
})();
