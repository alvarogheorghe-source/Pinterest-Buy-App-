"""Übersetzt die Startseite für die öffentliche Website (scripts/build_site.py -> /en/).

Deutsch bleibt die einzige Quelle (frontend/index.html). Die englischen Texte stehen in
website/en.json als "deutscher Text" -> "englischer Text". Übersetzt werden:
- sichtbare Texte zwischen den Tags
- Attribute, die Menschen lesen: aria-label, alt, title, placeholder
- Meta-Texte für Google & Teilen: description, og:title, og:description, og:image:alt
Skripte, Styles, SVG-Grafiken und Kommentare bleiben unangetastet.

missing() listet deutsche Texte ohne Übersetzung – der Build bricht dann ab, damit die
englische Seite nie halb deutsch online geht.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS = ROOT / "website" / "en.json"

# Bereiche, die nicht übersetzt werden (Code, Grafiken, Kommentare)
_PROTECTED = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>|<!--.*?-->",
                        re.DOTALL)
_TEXT = re.compile(r">([^<]+)<")
_ATTR = re.compile(r'(\s(?:aria-label|alt|title|placeholder)=")([^"]*)(")')
_META = re.compile(r'(<meta (?:name|property)="(?:description|og:title|og:description|og:image:alt)"'
                   r' content=")([^"]*)(")')


def load(path: Path = TRANSLATIONS) -> tuple[dict, set]:
    data = json.loads(path.read_text("utf-8"))
    return data["texts"], set(data.get("same", []))


def _key(raw: str) -> str:
    return " ".join(html.unescape(raw).split())


def _outside_protected(page: str, change) -> str:
    """change(seite) ohne Skripte/Grafiken/Kommentare: Die werden vorher durch Platzhalter-Tags
    ersetzt (<\x00 3 \x00>) – so bleibt ein Text direkt hinter einem Symbol (</svg>Text<)
    trotzdem als Text zwischen zwei Tags erkennbar."""
    kept = []

    def hide(match):
        kept.append(match.group(0))
        return f"<\x00{len(kept) - 1}\x00>"
    changed = change(_PROTECTED.sub(hide, page))
    return re.sub(r"<\x00(\d+)\x00>", lambda m: kept[int(m.group(1))], changed)


def texts(page: str) -> list[str]:
    """Alle übersetzbaren Texte einer Seite (normalisiert)."""
    found = []

    def collect(part: str) -> str:
        found.extend(_key(m.group(1)) for m in _TEXT.finditer(part))
        found.extend(_key(m.group(2)) for m in _ATTR.finditer(part))
        found.extend(_key(m.group(2)) for m in _META.finditer(part))
        return part
    _outside_protected(page, collect)
    return [t for t in found if any(c.isalpha() for c in t)]


def missing(page: str, translations: dict, same: set) -> list[str]:
    return sorted({t for t in texts(page) if t not in translations and t not in same})


def translate(page: str, translations: dict) -> str:
    def text(match):
        raw = match.group(1)
        key = _key(raw)
        if key not in translations:
            return match.group(0)
        lead = raw[:len(raw) - len(raw.lstrip())]
        trail = raw[len(raw.rstrip()):]
        return f">{lead}{html.escape(translations[key], quote=False)}{trail}<"

    def attr(match):
        key = _key(match.group(2))
        if key not in translations:
            return match.group(0)
        return f"{match.group(1)}{html.escape(translations[key])}{match.group(3)}"

    def change(part: str) -> str:
        part = _TEXT.sub(text, part)
        part = _ATTR.sub(attr, part)
        return _META.sub(attr, part)
    return _outside_protected(page, change)
