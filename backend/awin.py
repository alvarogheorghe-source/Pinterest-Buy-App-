"""Awin (Affiliate-Netzwerk) – Verbindung prüfen und Partnerprogramme anzeigen.

Awin vermittelt zwischen Malipin (Publisher) und vielen Shops (Advertiser). Pro Shop bewirbst
du dich einzeln; erst nach der Zusage gibt es Partnerlinks und Produkt-Feeds.

In .env (Werte aus dem Awin-Dashboard, nie in den Code!):
    AWIN_API_TOKEN=      Toolbox -> API-Zugangsdaten (OAuth2-Token)
    AWIN_PUBLISHER_ID=   deine Publisher-ID (Zahl)

Prüfen:   python -m backend.awin
Zeigt:    ob der Token funktioniert, bei welchen Shops du angenommen bist / noch wartest.

Die Produkte selbst (Bild, Preis …) kommen später über die Produkt-Feeds der angenommenen
Shops – dafür gibt es einen eigenen Feed-Schlüssel (Toolbox -> Create-a-Feed).
"""

import os

import httpx

API_URL = "https://api.awin.com"


class AwinError(Exception):
    pass


def configured() -> bool:
    return bool(os.getenv("AWIN_API_TOKEN", "").strip() and os.getenv("AWIN_PUBLISHER_ID", "").strip())


def _http() -> httpx.Client:
    """Eigene Funktion, damit Tests Awin simulieren können."""
    return httpx.Client(timeout=20)


def _get(path: str, params: dict | None = None):
    token = os.getenv("AWIN_API_TOKEN", "").strip()
    with _http() as client:
        response = client.get(API_URL + path, params=params,
                              headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 401:
        raise AwinError("Awin lehnt den Token ab – stimmt AWIN_API_TOKEN in .env?")
    if response.status_code in (403, 404):
        raise AwinError("Kein Zugriff auf dieses Konto – stimmt AWIN_PUBLISHER_ID in .env?")
    if response.status_code != 200:
        raise AwinError(f"Awin-Anfrage fehlgeschlagen ({response.status_code}).")
    return response.json()


def programmes(relationship: str) -> list[dict]:
    """relationship: "joined" (angenommen), "pending" (wartet), "notjoined" (noch nicht beworben)."""
    publisher = os.getenv("AWIN_PUBLISHER_ID", "").strip()
    data = _get(f"/publishers/{publisher}/programmes", {"relationship": relationship})
    return data if isinstance(data, list) else []


def _describe(programme: dict) -> str:
    region = (programme.get("primaryRegion") or {}).get("countryCode") or "?"
    return f"{programme.get('name', '?')}  ({region}, ID {programme.get('id', '?')})"


def main() -> None:
    from backend import config  # noqa: F401  (lädt .env)
    if not configured():
        print("AWIN_API_TOKEN / AWIN_PUBLISHER_ID fehlen in .env.")
        return
    try:
        joined, pending = programmes("joined"), programmes("pending")
    except (AwinError, httpx.HTTPError) as err:
        print(f"Fehler: {err}")
        return
    print("Verbindung zu Awin: ok\n")
    print(f"Angenommen ({len(joined)}):")
    for programme in joined:
        print("  ✓", _describe(programme))
    print(f"\nWartet auf Antwort ({len(pending)}):")
    for programme in pending:
        print("  …", _describe(programme))
    if not joined:
        print("\nNoch bei keinem Shop angenommen – im Awin-Dashboard unter Advertiser -> "
              "Programme suchen bei passenden Mode-/Wohn-Shops bewerben.")


if __name__ == "__main__":
    main()
