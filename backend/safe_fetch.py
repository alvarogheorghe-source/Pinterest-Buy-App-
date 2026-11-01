"""Bilder von fremden Adressen sicher laden.

Produktbild-Adressen kommen aus Feeds von Shops. Ein Shop könnte eine Adresse (oder eine
Weiterleitung) auf interne Dienste unseres Servers zeigen lassen (127.0.0.1, 169.254.…,
private Netze). Deshalb: nur http(s), nur öffentliche Ziele, jede Weiterleitung einzeln prüfen,
Größe begrenzen.
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx

MAX_REDIRECTS = 5
MAX_BYTES = 10 * 1024 * 1024


class UnsafeUrl(ValueError):
    """Adresse zeigt nicht ins öffentliche Internet (oder ist keine Web-Adresse)."""


def _addresses(host: str) -> list[str]:
    """IP-Adressen eines Namens. Unbekannter Name -> leer (der Abruf scheitert dann ohnehin)."""
    try:
        return [info[4][0] for info in socket.getaddrinfo(host, None)]
    except (socket.gaierror, UnicodeError, OSError):
        return []


def check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeUrl("keine Web-Adresse")
    host = parts.hostname.strip("[]")
    try:
        candidates = [host] if ipaddress.ip_address(host) else []
    except ValueError:
        if host == "localhost" or host.endswith(".localhost"):
            raise UnsafeUrl("internes Ziel")
        candidates = _addresses(host)
    for address in candidates:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise UnsafeUrl("internes Ziel")


def get(url: str, client: httpx.Client | None = None, timeout: float = 15,
        max_bytes: int = MAX_BYTES) -> bytes:
    """GET mit Prüfung jedes Ziels (auch nach Weiterleitungen). Gibt den Inhalt zurück."""
    own = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        for _ in range(MAX_REDIRECTS + 1):
            check_url(url)
            with client.stream("GET", url, follow_redirects=False) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("Bild ist zu groß")
                    chunks.append(chunk)
                return b"".join(chunks)
        raise ValueError("zu viele Weiterleitungen")
    finally:
        if own:
            client.close()
