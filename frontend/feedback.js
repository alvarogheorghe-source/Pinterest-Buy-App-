// 👍 / 👎 Buttons – gemeinsam genutzt von Shop (shop.js) und Detailseite (produkt.js).
// Muss VOR shop.js bzw. produkt.js geladen werden.

const THUMB_UP =
  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v12"/>' +
  '<path d="M15 5.9 14 10h5.8a2 2 0 0 1 1.9 2.6l-2.3 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9Z"/></svg>';
const THUMB_DOWN =
  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M17 14V2"/>' +
  '<path d="M9 18.1 10 14H4.2a2 2 0 0 1-1.9-2.6l2.3-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.8a2 2 0 0 0-1.8 1.1L12 22a3.1 3.1 0 0 1-3-3.9Z"/></svg>';

// Bewertung an das Backend schicken. vote = "like", "dislike" oder null (= löschen)
async function sendVote(productId, vote) {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, vote }),
  });
  return response.ok;
}

// Baut die zwei runden Buttons. "card" ist das Element, das bei 👎 durch einen
// Platzhalter mit "Rückgängig" ersetzt wird. card = null (z.B. auf der Detailseite):
// 👎 blendet nichts aus, der Button zeigt nur den Zustand.
function createVoteButtons(productId, currentVote, card) {
  const box = document.createElement("div");
  box.className = "vote-buttons";
  let vote = currentVote;

  const like = document.createElement("button");
  like.className = "vote-button";
  like.innerHTML = THUMB_UP; // fester Inhalt, keine Daten von außen
  like.setAttribute("aria-label", "Gefällt mir");

  const dislike = document.createElement("button");
  dislike.className = "vote-button";
  dislike.innerHTML = THUMB_DOWN;
  dislike.setAttribute("aria-label", "Gefällt mir nicht – ausblenden");

  function showState() {
    like.classList.toggle("active", vote === "like");
    like.setAttribute("aria-pressed", vote === "like");
    dislike.classList.toggle("active", vote === "dislike");
    dislike.setAttribute("aria-pressed", vote === "dislike");
  }

  like.addEventListener("click", async (event) => {
    event.preventDefault(); // nicht dem Link der Kachel folgen
    const newVote = vote === "like" ? null : "like"; // nochmal klicken = zurücknehmen
    if (await sendVote(productId, newVote)) {
      vote = newVote;
      showState();
      // Lucifer (bunny.js) freut sich mit
      if (newVote === "like") window.dispatchEvent(new CustomEvent("lucifer:like"));
    }
  });

  dislike.addEventListener("click", async (event) => {
    event.preventDefault();
    const newVote = vote === "dislike" ? null : "dislike";
    if (!(await sendVote(productId, newVote))) return;
    vote = newVote;
    if (newVote === "dislike") window.dispatchEvent(new CustomEvent("lucifer:dislike"));
    if (card && newVote === "dislike") {
      // Bei "Rückgängig" auch den Zustand der Buttons zurücksetzen
      dismiss(card, productId, () => { vote = null; showState(); });
    } else {
      showState();
    }
  });

  showState();
  box.append(like, dislike);
  return box;
}

// Nach 👎: Kachel durch einen Platzhalter ersetzen, mit "Rückgängig"
function dismiss(card, productId, onUndo) {
  const placeholder = document.createElement("div");
  placeholder.className = "dismissed";
  const text = document.createElement("p");
  text.textContent = "Ausgeblendet. Ähnliches zeigen wir dir seltener.";
  const undo = document.createElement("button");
  undo.className = "button secondary small";
  undo.textContent = "Rückgängig";
  undo.addEventListener("click", async () => {
    if (await sendVote(productId, null)) {
      placeholder.replaceWith(card); // Kachel wieder zeigen
      onUndo();
    }
  });
  placeholder.append(text, undo);
  card.replaceWith(placeholder);
}
