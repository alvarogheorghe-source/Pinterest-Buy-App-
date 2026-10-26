#!/bin/bash
# Startet Malipin mit einem Doppelklick (Mac).
# - beendet einen alten Server, der noch auf Port 8000 läuft
# - startet den Server neu
# - öffnet die Website im Browser
# Fenster offen lassen, solange du die App benutzt. Beenden: Ctrl + C oder Fenster schließen.

cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "Fehler: .venv fehlt. Einmalig im Terminal ausführen:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  read -r -p "Enter drücken zum Schließen"
  exit 1
fi

source .venv/bin/activate

# Neue Pakete nachinstallieren, falls requirements.txt sich geändert hat (sonst in 1–2 Sekunden fertig)
pip install -q -r requirements.txt

# Alten Server beenden (falls einer läuft)
lsof -ti :8000 | xargs kill 2>/dev/null
sleep 1

# Browser öffnen, sobald der Server bereit ist
(
  for _ in $(seq 30); do
    if curl -s -o /dev/null http://localhost:8000/health; then
      open http://localhost:8000
      exit 0
    fi
    sleep 0.5
  done
) &

echo "Malipin startet … (Fenster offen lassen)"
uvicorn backend.main:app --reload

echo
read -r -p "Server beendet. Enter drücken zum Schließen"
