// ♡ (merken) / 👎 Buttons – gemeinsam genutzt von Shop (shop.js) und Detailseite (produkt.js).
// ♡ = auf die Merkliste + Ähnliches nach oben, 👎 = ausblenden + Ähnliches nach unten.
// Muss VOR shop.js bzw. produkt.js geladen werden.

const HEART =
  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14c1.5-1.5 3-3.2 ' +
  '3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 ' +
  '1.5 4 3 5.5l7 7Z"/></svg>';
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
  if (response.ok) {
    // Allen Bescheid sagen (z.B. dem Merkliste-Zähler in der Kopfzeile, nav.js)
    window.dispatchEvent(new CustomEvent("merkliste:changed"));
  }
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
  like.className = "vote-button like";
  like.innerHTML = HEART; // fester Inhalt, keine Daten von außen
  like.setAttribute("aria-label", "Auf die Merkliste");

  const dislike = document.createElement("button");
  dislike.className = "vote-button";
  dislike.innerHTML = THUMB_DOWN;
  dislike.setAttribute("aria-label", "Nicht mein Stil – ausblenden");

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
      // Mali (bunny.js) freut sich mit
      if (newVote === "like") window.dispatchEvent(new CustomEvent("mali:like"));
    }
  });

  dislike.addEventListener("click", async (event) => {
    event.preventDefault();
    const newVote = vote === "dislike" ? null : "dislike";
    if (!(await sendVote(productId, newVote))) return;
    vote = newVote;
    if (newVote === "dislike") window.dispatchEvent(new CustomEvent("mali:dislike"));
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

// Pflicht-Hinweis aus den Etsy-API-Bedingungen: zeigen, sobald Etsy-Produkte auf der Seite sind
function showEtsyAttribution(products) {
  const note = document.getElementById("etsy-attribution");
  if (note) note.hidden = !products.some((p) => p.shop.startsWith("Etsy"));
}

// Name des Shops für "Link zu …": der Shop vor dem "·" ("eBay · Second Hand" -> eBay)
function shopName(product) {
  return product.shop.split(" · ")[0];
}
