"""Schutz vor zu vielen Foto-Uploads: die Bilderkennung braucht viel Rechenzeit.

Pro Person (IP-Adresse) höchstens LIMIT Fotos in WINDOW Sekunden. Gezählt wird nur im
Arbeitsspeicher, nichts davon wird gespeichert.
"""

import threading
import time
from collections import defaultdict, deque

LIMIT = 10
WINDOW = 10 * 60

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def allow(key: str, limit: int = LIMIT, window: float = WINDOW) -> bool:
    """True, wenn diese Person noch darf (und zählt den Versuch mit)."""
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        # Alte Einträge anderer Personen wegräumen, damit der Speicher nicht wächst
        if len(_hits) > 10_000:
            for other in [k for k, v in _hits.items() if not v or v[-1] <= now - window]:
                del _hits[other]
        return True


def reset() -> None:
    with _lock:
        _hits.clear()
