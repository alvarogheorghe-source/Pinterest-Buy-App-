// Konto-Seite: Login-Status anzeigen, Boards auswählen, Pins laden.

const statusText = document.getElementById("status");
const loginSection = document.getElementById("login-section");
const boardsSection = document.getElementById("boards-section");
const boardList = document.getElementById("board-list");
const saveMessage = document.getElementById("save-message");

// Beim Laden der Seite: Sind wir mit Pinterest verbunden?
async function init() {
  // Fehler aus dem Login (z.B. Nutzer hat abgelehnt) steht in der URL
  const error = new URLSearchParams(location.search).get("error");

  const me = await fetch("/api/me").then((r) => r.json());
  if (!me.connected) {
    statusText.textContent = error ? `Login abgebrochen (${error}).` : "Nicht verbunden.";
    loginSection.hidden = false;
    return;
  }

  statusText.textContent = `Verbunden als ${me.username}`;
  boardsSection.hidden = false;
  await loadBoards();
  await showSavedPins();
}

async function loadBoards() {
  const response = await fetch("/api/boards");
  if (!response.ok) {
    statusText.textContent = "Boards konnten nicht geladen werden.";
    return;
  }
  const boards = await response.json();

  boardList.innerHTML = "";
  if (boards.length === 0) {
    boardList.textContent = "Keine Boards gefunden.";
  }
  for (const board of boards) {
    boardList.appendChild(renderBoard(board));
  }
}

// Baut eine Listenzeile mit Checkbox. Wir nutzen textContent statt innerHTML,
// damit Board-Namen nie als HTML ausgeführt werden.
function renderBoard(board) {
  const li = document.createElement("li");

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `board-${board.id}`;
  checkbox.value = board.id;
  checkbox.checked = board.selected;

  const label = document.createElement("label");
  label.htmlFor = checkbox.id;
  label.textContent = board.name;
  const count = document.createElement("div");
  count.className = "muted";
  count.textContent = `${board.pin_count} Pins`;
  label.appendChild(count);

  li.appendChild(checkbox);
  if (board.cover_url) {
    const img = document.createElement("img");
    img.src = board.cover_url;
    img.alt = "";
    li.appendChild(img);
  }
  li.appendChild(label);
  return li;
}

document.getElementById("save-button").addEventListener("click", async () => {
  const boardIds = [...boardList.querySelectorAll("input:checked")].map((cb) => cb.value);
  const response = await fetch("/api/boards/selection", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board_ids: boardIds }),
  });
  saveMessage.textContent = response.ok
    ? `${boardIds.length} Board(s) gespeichert.`
    : "Speichern fehlgeschlagen.";
});

// --- Pins (Schritt 3) ---

const pinsMessage = document.getElementById("pins-message");
const pinGrid = document.getElementById("pin-grid");

// Zeigt die schon gespeicherten Pins (fragt Pinterest NICHT neu an)
async function showSavedPins() {
  const data = await fetch("/api/pins").then((r) => r.json());
  if (data.pins.length === 0) {
    pinsMessage.textContent = "Noch keine Pins geladen.";
    return;
  }
  const date = new Date(data.fetched_at * 1000).toLocaleString("de-AT");
  pinsMessage.textContent = `${data.pins.length} Pins gespeichert (Stand: ${date})`;

  // Stilprofil (Schritt 5): die häufigsten Farben und Stile
  // Zwei Stilprofile: Mode und Wohnen & Deko
  const profiles = await fetch("/api/profile").then((r) => r.json());
  const lines = [];
  for (const [department, name] of [["mode", "Mode"], ["wohnen", "Wohnen & Deko"]]) {
    const profile = profiles[department];
    const terms = [...profile.top_colors, ...profile.top_styles];
    if (terms.length) lines.push(`${name}: ${terms.join(" · ")}`);
  }
  document.getElementById("profile-text").textContent = lines.length
    ? `Dein Stil – ${lines.join("  |  ")}`
    : "In deinen Pins wurden noch keine Farb- oder Stilwörter gefunden.";
  document.getElementById("shop-link").hidden = false;

  // Vorschau: die ersten 24 Bilder
  pinGrid.innerHTML = "";
  for (const pin of data.pins.slice(0, 24)) {
    if (!pin.image_url) continue;
    const img = document.createElement("img");
    img.src = pin.image_url;
    img.alt = pin.title;
    img.title = pin.title;
    pinGrid.appendChild(img);
  }
}

document.getElementById("pins-button").addEventListener("click", async () => {
  pinsMessage.textContent = "Lade Pins von Pinterest…";
  const response = await fetch("/api/pins/refresh", { method: "POST" });
  const result = await response.json();
  if (!response.ok) {
    pinsMessage.textContent = result.detail; // z.B. "Keine Boards ausgewählt."
    return;
  }
  await showSavedPins();
});

document.getElementById("logout-button").addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST" });
  location.href = "/konto.html";
});

// --- Bewertungen (👍/👎) ---

const feedbackText = document.getElementById("feedback-text");
const feedbackReset = document.getElementById("feedback-reset");

async function showFeedback() {
  const votes = Object.values(await fetch("/api/feedback").then((r) => r.json()));
  const likes = votes.filter((v) => v.vote === "like").length;
  const dislikes = votes.length - likes;
  feedbackText.textContent = votes.length
    ? `${likes} × 👍 und ${dislikes} × 👎. Damit sortieren wir deine Vorschläge.`
    : "Noch keine Bewertungen. Bewerte Produkte im Shop mit 👍 oder 👎.";
  feedbackReset.hidden = votes.length === 0;
}

feedbackReset.addEventListener("click", async () => {
  await fetch("/api/feedback", { method: "DELETE" });
  showFeedback();
});

init();
showFeedback();
