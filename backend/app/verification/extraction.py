import re
from dataclasses import dataclass

from app.constructor.node_types import NodeType

_SURNAME = r"[A-ZÁÉÍÓÚÑÜ][a-záéíóúñüA-ZÁÉÍÓÚÑÜ''\-]+"
_YEAR = r"\d{4}[a-z]?|s\.f\."
# Surnames separated by "," / "&" / " y ", optionally ending in "et al."
_AUTHORS = (
    rf"{_SURNAME}(?:\s*,\s*{_SURNAME})*(?:\s+(?:y|&)\s+{_SURNAME})?"
    rf"(?:\s+et\s+al\.?)?"
)
_PAGES = r"(?:\s*,\s*pp?\.\s*[\d\s,–\-]+)?"

_PAREN_RE = re.compile(rf"(?P<auth>{_AUTHORS})\s*,\s*(?P<year>{_YEAR}){_PAGES}")
_PAREN_NO_COMMA_RE = re.compile(rf"(?P<auth>{_AUTHORS})\s+(?P<year>\d{{4}}[a-z]?)")
_NARRATIVE_RE = re.compile(rf"(?P<auth>{_AUTHORS})\s+\((?P<year>{_YEAR})\)")
_ET_AL_RE = re.compile(r"\bet\s+al\.?")


@dataclass(frozen=True)
class Citation:
    node_type: NodeType
    raw: str
    surname: str
    surnames: tuple[str, ...]
    year: str  # "2020", "2020a" o "s.f."
    narrative: bool
    et_al: bool
    missing_comma: bool = False


def _parse_authors(text: str) -> tuple[tuple[str, ...], bool]:
    et_al = bool(_ET_AL_RE.search(text))
    cleaned = _ET_AL_RE.sub("", text)
    parts = re.split(r"\s*,\s*|\s+(?:y|&)\s+", cleaned)
    return tuple(p.strip() for p in parts if p.strip()), et_al


def extract_citations(node_type: NodeType, content: str) -> list[Citation]:
    found: list[tuple[int, Citation]] = []

    for m in re.finditer(r"\(([^()]*)\)", content):
        inner = m.group(1)
        offset = 0
        for seg in inner.split(";"):
            pos = m.start() + offset
            offset += len(seg) + 1
            seg = seg.strip()
            cm, missing = _PAREN_RE.fullmatch(seg), False
            if cm is None:
                cm = _PAREN_NO_COMMA_RE.fullmatch(seg)
                missing = cm is not None
            if cm is None:
                continue
            surnames, et_al = _parse_authors(cm.group("auth"))
            found.append((pos, Citation(
                node_type=node_type, raw=f"({seg})", surname=surnames[0],
                surnames=surnames, year=cm.group("year"), narrative=False,
                et_al=et_al, missing_comma=missing,
            )))

    for m in _NARRATIVE_RE.finditer(content):
        surnames, et_al = _parse_authors(m.group("auth"))
        found.append((m.start(), Citation(
            node_type=node_type, raw=m.group(0), surname=surnames[0],
            surnames=surnames, year=m.group("year"), narrative=True, et_al=et_al,
        )))

    found.sort(key=lambda t: t[0])
    return [c for _, c in found]
