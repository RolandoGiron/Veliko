# Velvyko — Fase 2: Verificación de citas (APA + anti-alucinación) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On-demand verification of APA in-text citations inside the 6 research nodes: deterministic extraction + APA-7 format checks, existence verification against Crossref/OpenAlex (anti-hallucination), and a tier-gated LLM style review — surfaced in a project-level frontend panel.

**Architecture:** New backend module `app/verification/` following the existing modular-monolith pattern (extraction → checks → external lookup with DB cache → optional LLM via the existing `llm_gateway` → persisted run). The gateway is generalized to accept any Pydantic `response_model`. All external failures degrade honestly (`no_verificable`, never "inventada"); LLM failure degrades the run instead of aborting. Spec: `docs/superpowers/specs/2026-06-11-velvyko-citation-verification-design.md`.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 async · httpx (runtime, new) · Crossref + OpenAlex REST · instructor via existing `llm_gateway` · Alembic · React + Vite + TS + TanStack Query.

**Conventions (same as MVP):** run backend commands from `backend/` with `.venv/bin/python -m pytest …` (the venv lives at `backend/.venv`). Every task is TDD: failing test → minimal code → green → commit.

---

## ESTADO DE EJECUCIÓN — COMPLETADO 2026-06-14 (Fase 2 lista para shipping)

Modo de ejecución: **superpowers:subagent-driven-development** (un implementador por tarea + review de spec + review de calidad). Commits directos a `main` (convención del repo). Estado final: **suite backend 113/113 verde, build frontend limpio**, revisión final de toda la feature aprobada (Ready to merge: Yes).

| Tarea | Estado | Commit | Notas |
|---|---|---|---|
| 1. Config + httpx | ✅ | `7d34e9f` | |
| 2. Extracción | ✅ | `a5d7ba7` + `c1b8c31` | |
| 3. Checks APA-7 | ✅ | `b263439` | |
| 4. Modelos | ✅ | `cbb4be9` | |
| 5. Lookup | ✅ | `34097f3` + `dad976a` | Fixes review 1-4,6,8 |
| 6. Gateway response_model | ✅ | `fad1321` + `a802835` | Genérico, default CoherenceVerdict |
| 7. Contrato LLM + prompts | ✅ | `9e24911` | |
| 8. Rate limiter + cuota | ✅ | `42f7927` | |
| 9. Pipeline | ✅ | `52ce9d8` | |
| 10. Endpoints HTTP | ✅ | `019e60e` + `021d5ad` | Fix: ProjectNotFound sentinel |
| 11. Migración Alembic | ✅ | `2b5599b` | |
| 12. Frontend panel | ✅ | `205724f` + `ac73dc4` | + polish .muted/a11y |
| 13. Evals (no-CI) | ✅ | `7ea8bbc` | |
| 14. Verificación + docs | ✅ | `67f8255` | |
| Extra (review final) | ✅ | `7c74548` | stale-negative no se resirve en outage |

**Follow-ups Minor diferidos** (de la review final, no bloqueantes): (a) spec §10 menciona config `citation_llm_tiers` que no se implementó — los tiers están hardcoded en `pipeline.py` (`LLM_TIERS`); decidir si añadir la setting o quitar del spec. (b) Tipos TS `format_issues`/`project_issues` son un mirror un poco estrecho (omiten `citation_raw`); cosmético. (c) httpx singleton en `service.py` sin cierre en lifespan (MVP-aceptable). (d) `coherence/router.py` tiene el mismo `except LookupError→404` masking que se corrigió en verification — alinear si se quiere.

**Decisiones ya tomadas con el usuario (no volver a preguntar):** solo Fase 2; citas en-texto dentro de los 6 nodos (sin sección de referencias); validación APA híbrida determinista+LLM; ejecución con subagentes; diseño y spec aprobados (`docs/superpowers/specs/2026-06-11-velvyko-citation-verification-design.md`).

---

## File Structure

```
backend/app/verification/
  __init__.py            # empty
  extraction.py          # Citation dataclass + extract_citations()
  apa_checks.py          # ApaIssue + run_apa_checks()
  lookup.py              # ExistenceStatus, Candidate, LookupResult, LookupClient,
                         #   CrossrefOpenAlexClient, cached_lookup()
  contracts.py           # StyleIssue, CitationStyleReview (LLM contract)
  models.py              # CitationRun, CitationFinding, CitationLookup
  pipeline.py            # verify_citations() orchestration
  schemas.py             # CandidateOut, FindingOut, CitationRunOut
  service.py             # get_lookup_client(), get_latest_run()
  router.py              # POST/GET /api/projects/{pid}/verify-citations
backend/app/entitlements/ratelimit.py   # SlidingWindowLimiter (new)
backend/app/entitlements/quota.py       # modified: count CitationRun llm_used too
backend/app/llm_gateway/{base,gateway}.py + providers/   # modified: response_model param
backend/app/i18n/prompts.py             # add citation prompts
backend/alembic/versions/0002_citations.py
backend/tests/unit/test_extraction.py, test_apa_checks.py, test_lookup.py, test_ratelimit.py
backend/tests/integration/test_verification_pipeline.py, test_verification_api.py
backend/tests/evals/citation_golden.py, run_citation_evals.py
frontend/src/api/types.ts, client.ts    # modified
frontend/src/components/VerificationPanel.tsx   # new
frontend/src/pages/ProjectPage.tsx      # modified
```

---

## Task 1: Config + runtime httpx dependency

**Files:**
- Modify: `backend/pyproject.toml` (move httpx to runtime deps), `backend/app/config.py`, `.env.example`

- [ ] **Step 1: Add httpx to runtime dependencies** — in `backend/pyproject.toml` `[project] dependencies`, add `"httpx>=0.27",` (keep the copy in `[project.optional-dependencies].dev`; duplication is harmless).

- [ ] **Step 2: Add settings** — in `backend/app/config.py`, inside `Settings`, after `llm_timeout_s`:

```python
    lookup_timeout_s: float = 8.0
    lookup_cache_ttl_days: int = 30
    crossref_mailto: str = "admin@srv1533829.hstgr.cloud"
```

- [ ] **Step 3: Document in `.env.example`** — append:

```bash
# --- Citation verification (Fase 2) ---
CROSSREF_MAILTO=admin@srv1533829.hstgr.cloud
```

- [ ] **Step 4: Install + sanity check**

Run: `cd backend && .venv/bin/pip install -e ".[dev]" -q && .venv/bin/python -c "from app.config import get_settings; print(get_settings().lookup_timeout_s)"`
Expected: `8.0`

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py .env.example
git commit -m "chore(verification): httpx runtime dep + lookup settings"
```

---

## Task 2: Extraction — APA in-text citations (unit, TDD)

**Files:**
- Create: `backend/app/verification/__init__.py` (empty), `backend/app/verification/extraction.py`
- Test: `backend/tests/unit/test_extraction.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_extraction.py`

```python
from app.constructor.node_types import NodeType
from app.verification.extraction import extract_citations


def _ext(text: str):
    return extract_citations(NodeType.problema, text)


def test_narrative_single_author():
    [c] = _ext("Como demostró García (2020), el problema persiste.")
    assert (c.surname, c.year, c.narrative) == ("García", "2020", True)
    assert c.surnames == ("García",)
    assert c.et_al is False


def test_parenthetical_single_author():
    [c] = _ext("El problema persiste (García, 2020).")
    assert (c.surname, c.year, c.narrative) == ("García", "2020", False)
    assert c.raw == "(García, 2020)"


def test_parenthetical_two_authors_ampersand():
    [c] = _ext("Esto se confirmó (García & López, 2019).")
    assert c.surnames == ("García", "López")


def test_narrative_two_authors_y():
    [c] = _ext("García y López (2019) confirmaron esto.")
    assert c.surnames == ("García", "López")
    assert c.narrative is True


def test_et_al():
    [c] = _ext("Según García et al. (2021), es así.")
    assert c.et_al is True
    assert c.surname == "García"


def test_multiple_citations_in_one_paren():
    cs = _ext("Varios lo afirman (García, 2019; López, 2020).")
    assert [(c.surname, c.year) for c in cs] == [("García", "2019"), ("López", "2020")]


def test_with_page_number():
    [c] = _ext("Se definió así (García et al., 2021, p. 23).")
    assert (c.surname, c.year) == ("García", "2021")


def test_year_suffix_and_sf():
    cs = _ext("Primero (García, 2020a) y luego (López, s.f.).")
    assert [c.year for c in cs] == ["2020a", "s.f."]


def test_missing_comma_detected():
    [c] = _ext("Mal citado (García 2020).")
    assert c.missing_comma is True
    assert (c.surname, c.year) == ("García", "2020")


def test_plain_parentheses_ignored():
    assert _ext("El acrónimo (OMS) y el dato (45%) no son citas.") == []


def test_ordered_by_position():
    cs = _ext("López (2018) lo dijo antes (García, 2020).")
    assert [c.surname for c in cs] == ["López", "García"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_extraction.py -v`
Expected: FAIL — `ModuleNotFoundError: app.verification`

- [ ] **Step 3: Implement** — `backend/app/verification/extraction.py` (and empty `backend/app/verification/__init__.py`)

```python
import re
from dataclasses import dataclass

from app.constructor.node_types import NodeType

_SURNAME = r"[A-ZÁÉÍÓÚÑÜ][a-záéíóúñüA-ZÁÉÍÓÚÑÜ'’\-]+"
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_extraction.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/verification/__init__.py backend/app/verification/extraction.py backend/tests/unit/test_extraction.py
git commit -m "feat(verification): deterministic APA in-text citation extraction"
```

---

## Task 3: APA-7 format checks (unit, TDD)

**Files:**
- Create: `backend/app/verification/apa_checks.py`
- Test: `backend/tests/unit/test_apa_checks.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_apa_checks.py`

```python
from datetime import date

from app.constructor.node_types import NodeType
from app.verification.apa_checks import run_apa_checks
from app.verification.extraction import extract_citations

TODAY = date(2026, 6, 11)


def _issues(text: str):
    return run_apa_checks(extract_citations(NodeType.problema, text), TODAY)


def test_no_citations_informative():
    [i] = run_apa_checks([], TODAY)
    assert (i.code, i.severity) == ("sin_citas", "menor")


def test_clean_citation_no_issues():
    assert _issues("Lo dijo (García, 2020).") == []


def test_missing_comma_flagged_mayor():
    issues = _issues("Mal (García 2020).")
    assert [(i.code, i.severity) for i in issues] == [("falta_coma", "mayor")]


def test_ampersand_in_narrative_flagged():
    issues = _issues("García & López (2019) lo dijeron.")
    assert any(i.code == "ampersand_en_narrativa" and i.severity == "menor" for i in issues)


def test_y_in_parenthetical_flagged():
    issues = _issues("Lo dijeron (García y López, 2019).")
    assert any(i.code == "y_en_parentetica" and i.severity == "menor" for i in issues)


def test_three_plus_authors_listed_flagged():
    issues = _issues("Lo dijeron (García, López & Pérez, 2019).")
    assert any(i.code == "demasiados_autores" and i.severity == "mayor" for i in issues)


def test_et_al_not_flagged_as_too_many():
    assert _issues("Lo dijeron (García et al., 2019).") == []


def test_future_year_flagged():
    issues = _issues("Se publicará (García, 2030).")
    assert any(i.code == "anio_futuro" and i.severity == "mayor" for i in issues)


def test_next_year_tolerated():
    assert _issues("En prensa (García, 2027).") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_apa_checks.py -v`
Expected: FAIL — module missing

- [ ] **Step 3: Implement** — `backend/app/verification/apa_checks.py`

```python
import re
from dataclasses import dataclass
from datetime import date

from app.verification.extraction import Citation


@dataclass(frozen=True)
class ApaIssue:
    severity: str  # critica | mayor | menor
    code: str
    message: str
    citation_raw: str | None = None


def run_apa_checks(citations: list[Citation], today: date) -> list[ApaIssue]:
    if not citations:
        return [ApaIssue(
            "menor", "sin_citas",
            "El proyecto no contiene ninguna cita en-texto APA (Autor, año).",
        )]

    issues: list[ApaIssue] = []
    for c in citations:
        if c.missing_comma:
            issues.append(ApaIssue(
                "mayor", "falta_coma",
                f"Falta la coma antes del año en {c.raw}; APA: (Autor, año).",
                c.raw,
            ))
        if c.narrative and "&" in c.raw:
            issues.append(ApaIssue(
                "menor", "ampersand_en_narrativa",
                f"En citas narrativas se escribe 'y' en vez de '&': {c.raw}.",
                c.raw,
            ))
        if not c.narrative and re.search(r"\by\b", c.raw):
            issues.append(ApaIssue(
                "menor", "y_en_parentetica",
                f"Dentro de paréntesis APA usa '&' en vez de 'y': {c.raw}.",
                c.raw,
            ))
        if len(c.surnames) >= 3:
            issues.append(ApaIssue(
                "mayor", "demasiados_autores",
                f"Con 3+ autores cita solo el primero seguido de 'et al.': {c.raw}.",
                c.raw,
            ))
        if c.year[:4].isdigit() and int(c.year[:4]) > today.year + 1:
            issues.append(ApaIssue(
                "mayor", "anio_futuro",
                f"El año de {c.raw} está en el futuro; verifica la fecha.",
                c.raw,
            ))
    return issues
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_apa_checks.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/verification/apa_checks.py backend/tests/unit/test_apa_checks.py
git commit -m "feat(verification): deterministic APA-7 format checks"
```

---

## Task 4: Persistence models + conftest wiring

**Files:**
- Create: `backend/app/verification/models.py`
- Modify: `backend/tests/conftest.py` (model import)

- [ ] **Step 1: Implement models** — `backend/app/verification/models.py` (no standalone test; exercised by Tasks 5/9/10 against the sqlite fixture)

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CitationRun(Base):
    __tablename__ = "citation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("research_projects.id"), index=True
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    project_issues: Mapped[list] = mapped_column(JSON, default=list)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_issues: Mapped[list] = mapped_column(JSON, default=list)
    llm_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )


class CitationFinding(Base):
    __tablename__ = "citation_findings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("citation_runs.id"), index=True)
    node_type: Mapped[str] = mapped_column(String, nullable=False)
    raw: Mapped[str] = mapped_column(String, nullable=False)
    surname: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[str] = mapped_column(String, nullable=False)
    narrative: Mapped[bool] = mapped_column(Boolean, default=False)
    format_issues: Mapped[list] = mapped_column(JSON, default=list)
    existence_status: Mapped[str] = mapped_column(String, nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list)


class CitationLookup(Base):
    __tablename__ = "citation_lookups"

    surname_norm: Mapped[str] = mapped_column(String, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 2: Register models in the test metadata** — in `backend/tests/conftest.py`, after `import app.coherence.models  # noqa: F401` add:

```python
import app.verification.models  # noqa: F401
```

- [ ] **Step 3: Verify nothing broke**

Run: `cd backend && .venv/bin/python -m pytest tests/unit tests/integration -q`
Expected: all existing tests still pass (54+)

- [ ] **Step 4: Commit**

```bash
git add backend/app/verification/models.py backend/tests/conftest.py
git commit -m "feat(verification): citation run/finding/lookup-cache models"
```

---

## Task 5: Lookup — Crossref/OpenAlex client + DB cache (unit, TDD)

**Files:**
- Create: `backend/app/verification/lookup.py`
- Test: `backend/tests/unit/test_lookup.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_lookup.py`

```python
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.verification.lookup import (
    Candidate,
    CrossrefOpenAlexClient,
    ExistenceStatus,
    LookupResult,
    cached_lookup,
    normalize_surname,
)
from app.verification.models import CitationLookup

CROSSREF_OK = {
    "message": {"items": [{
        "title": ["Self-efficacy: Toward a unifying theory"],
        "DOI": "10.1037/0033-295x.84.2.191",
        "author": [{"family": "Bandura"}],
    }]}
}
OPENALEX_OK = {
    "results": [{
        "title": "Self-efficacy",
        "doi": "https://doi.org/10.1037/0033-295x.84.2.191",
        "authorships": [{"author": {"display_name": "Albert Bandura"}}],
    }]
}
EMPTY_CROSSREF = {"message": {"items": []}}
EMPTY_OPENALEX = {"results": []}


def _client(handler) -> CrossrefOpenAlexClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return CrossrefOpenAlexClient(http, mailto="t@e.st", timeout_s=2.0)


def test_normalize_surname_strips_diacritics():
    assert normalize_surname("Gárcía-Müller") == "garcia-muller"


async def test_found_in_both_sources():
    def handler(req: httpx.Request) -> httpx.Response:
        body = CROSSREF_OK if "crossref" in req.url.host else OPENALEX_OK
        return httpx.Response(200, json=body)

    r = await _client(handler).lookup("Bandura", 1977)
    assert r.status == ExistenceStatus.encontrada
    assert len(r.candidates) == 2
    assert {c.source for c in r.candidates} == {"crossref", "openalex"}


async def test_no_author_match_is_no_encontrada():
    def handler(req: httpx.Request) -> httpx.Response:
        body = EMPTY_CROSSREF if "crossref" in req.url.host else EMPTY_OPENALEX
        return httpx.Response(200, json=body)

    r = await _client(handler).lookup("Zzyzwicz", 2019)
    assert r.status == ExistenceStatus.no_encontrada
    assert r.candidates == []


async def test_results_without_matching_surname_filtered():
    def handler(req: httpx.Request) -> httpx.Response:
        body = CROSSREF_OK if "crossref" in req.url.host else EMPTY_OPENALEX
        return httpx.Response(200, json=body)

    r = await _client(handler).lookup("García", 1977)  # Bandura != García
    assert r.status == ExistenceStatus.no_encontrada


async def test_one_source_down_still_works():
    def handler(req: httpx.Request) -> httpx.Response:
        if "crossref" in req.url.host:
            return httpx.Response(500)
        return httpx.Response(200, json=OPENALEX_OK)

    r = await _client(handler).lookup("Bandura", 1977)
    assert r.status == ExistenceStatus.encontrada
    assert [c.source for c in r.candidates] == ["openalex"]


async def test_both_sources_down_is_no_verificable():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom")

    r = await _client(handler).lookup("Bandura", 1977)
    assert r.status == ExistenceStatus.no_verificable


async def test_cached_lookup_hits_cache(db_session):
    class Exploding:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            raise AssertionError("must not be called on cache hit")

    now = datetime.now(timezone.utc)
    db_session.add(CitationLookup(
        surname_norm="bandura", year=1977, status="encontrada",
        candidates=[{"title": "t", "doi": "d", "year": 1977, "source": "crossref"}],
        fetched_at=now,
    ))
    await db_session.flush()

    r = await cached_lookup(db_session, Exploding(), "Bandura", 1977, now=now, ttl_days=30)
    assert r.status == ExistenceStatus.encontrada
    assert r.candidates[0].doi == "d"


async def test_cached_lookup_miss_stores(db_session):
    class Fake:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            return LookupResult(status=ExistenceStatus.no_encontrada)

    now = datetime.now(timezone.utc)
    r = await cached_lookup(db_session, Fake(), "Zzyzwicz", 2019, now=now, ttl_days=30)
    assert r.status == ExistenceStatus.no_encontrada
    row = await db_session.get(CitationLookup, ("zzyzwicz", 2019))
    assert row is not None and row.status == "no_encontrada"


async def test_cached_lookup_does_not_cache_failures(db_session):
    class Fake:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            return LookupResult(status=ExistenceStatus.no_verificable)

    now = datetime.now(timezone.utc)
    await cached_lookup(db_session, Fake(), "Bandura", 1977, now=now, ttl_days=30)
    assert await db_session.get(CitationLookup, ("bandura", 1977)) is None


async def test_cached_lookup_expired_refetches(db_session):
    calls = []

    class Fake:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            calls.append(1)
            return LookupResult(status=ExistenceStatus.no_encontrada)

    now = datetime.now(timezone.utc)
    db_session.add(CitationLookup(
        surname_norm="bandura", year=1977, status="encontrada", candidates=[],
        fetched_at=now - timedelta(days=31),
    ))
    await db_session.flush()

    r = await cached_lookup(db_session, Fake(), "Bandura", 1977, now=now, ttl_days=30)
    assert calls == [1]
    assert r.status == ExistenceStatus.no_encontrada
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_lookup.py -v`
Expected: FAIL — module missing

- [ ] **Step 3: Implement** — `backend/app/verification/lookup.py`

```python
import asyncio
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Protocol

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.verification.models import CitationLookup


class ExistenceStatus(StrEnum):
    encontrada = "encontrada"
    no_encontrada = "no_encontrada"
    no_verificable = "no_verificable"


@dataclass(frozen=True)
class Candidate:
    title: str
    doi: str | None
    year: int | None
    source: str  # crossref | openalex


@dataclass(frozen=True)
class LookupResult:
    status: ExistenceStatus
    candidates: list[Candidate] = field(default_factory=list)


class LookupClient(Protocol):
    async def lookup(self, surname: str, year: int) -> LookupResult: ...


def normalize_surname(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


class CrossrefOpenAlexClient:
    def __init__(self, http: httpx.AsyncClient, mailto: str, timeout_s: float) -> None:
        self._http = http
        self._mailto = mailto
        self._timeout = timeout_s

    async def lookup(self, surname: str, year: int) -> LookupResult:
        target = normalize_surname(surname)
        results = await asyncio.gather(
            self._crossref(surname, year, target),
            self._openalex(surname, year, target),
            return_exceptions=True,
        )
        if all(isinstance(r, BaseException) for r in results):
            return LookupResult(status=ExistenceStatus.no_verificable)
        candidates: list[Candidate] = []
        for r in results:
            if not isinstance(r, BaseException):
                candidates.extend(r)
        if not candidates:
            return LookupResult(status=ExistenceStatus.no_encontrada)
        return LookupResult(status=ExistenceStatus.encontrada, candidates=candidates[:3])

    async def _crossref(self, surname: str, year: int, target: str) -> list[Candidate]:
        r = await self._http.get(
            "https://api.crossref.org/works",
            params={
                "query.author": surname,
                "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
                "rows": 5,
                "mailto": self._mailto,
            },
            timeout=self._timeout,
        )
        r.raise_for_status()
        out: list[Candidate] = []
        for item in r.json().get("message", {}).get("items", []):
            families = [a.get("family", "") for a in item.get("author", [])]
            if not any(normalize_surname(f) == target for f in families if f):
                continue
            title = (item.get("title") or [""])[0]
            out.append(Candidate(title=title, doi=item.get("DOI"), year=year,
                                 source="crossref"))
        return out

    async def _openalex(self, surname: str, year: int, target: str) -> list[Candidate]:
        r = await self._http.get(
            "https://api.openalex.org/works",
            params={
                "search": surname,
                "filter": f"publication_year:{year}",
                "per-page": 5,
                "mailto": self._mailto,
            },
            timeout=self._timeout,
        )
        r.raise_for_status()
        out: list[Candidate] = []
        for item in r.json().get("results", []):
            names = [
                a.get("author", {}).get("display_name", "")
                for a in item.get("authorships", [])
            ]
            tokens = {normalize_surname(t) for n in names for t in n.split()}
            if target not in tokens:
                continue
            out.append(Candidate(title=item.get("title") or "", doi=item.get("doi"),
                                 year=year, source="openalex"))
        return out


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def cached_lookup(
    session: AsyncSession,
    client: LookupClient,
    surname: str,
    year: int,
    *,
    now: datetime,
    ttl_days: int,
) -> LookupResult:
    key = normalize_surname(surname)
    row = await session.get(CitationLookup, (key, year))
    if row is not None and _as_aware(row.fetched_at) >= now - timedelta(days=ttl_days):
        return LookupResult(
            status=ExistenceStatus(row.status),
            candidates=[Candidate(**c) for c in row.candidates],
        )
    result = await client.lookup(surname, year)
    if result.status is not ExistenceStatus.no_verificable:
        if row is None:
            row = CitationLookup(surname_norm=key, year=year)
            session.add(row)
        row.status = result.status.value
        row.candidates = [asdict(c) for c in result.candidates]
        row.fetched_at = now
        await session.flush()
    return result
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_lookup.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/verification/lookup.py backend/tests/unit/test_lookup.py
git commit -m "feat(verification): crossref/openalex lookup with fail-closed states + db cache"
```

---

## Task 6: Generalize llm_gateway to arbitrary response models

**Files:**
- Modify: `backend/app/llm_gateway/base.py`, `backend/app/llm_gateway/gateway.py`, `backend/app/llm_gateway/providers/anthropic_provider.py`, `backend/app/llm_gateway/providers/openai_provider.py`
- Test: modify `backend/tests/unit/test_gateway.py`

The gateway/providers are hardcoded to `CoherenceVerdict`. Add a `response_model` parameter (default `CoherenceVerdict`, so the coherence pipeline and its fakes keep working unchanged).

- [ ] **Step 1: Write the failing test** — append to `backend/tests/unit/test_gateway.py`

```python
from pydantic import BaseModel


class _Tiny(BaseModel):
    ok: bool


def test_gateway_passes_response_model_through():
    seen = {}

    class RecordingProvider:
        def validate(self, *, model, system_prompt, user_prompt, timeout_s,
                     response_model):
            seen["rm"] = response_model
            from app.llm_gateway.base import LLMResult
            return LLMResult(verdict=_Tiny(ok=True), model_used=model,
                             tokens_used=1, cost_usd=0.0)

    from datetime import date
    from app.llm_gateway.breaker import CircuitBreaker
    from app.llm_gateway.budget import DailyBudget
    from app.llm_gateway.gateway import LLMGateway

    gw = LLMGateway(RecordingProvider(), DailyBudget(limit_usd=10),
                    CircuitBreaker(5, 60), timeout_s=5)
    out = gw.validate(model="m", system_prompt="s", user_prompt="u",
                      today=date(2026, 6, 11), response_model=_Tiny)
    assert seen["rm"] is _Tiny
    assert out.verdict.ok is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_gateway.py -v`
Expected: new test FAILS (`unexpected keyword argument 'response_model'`); old ones pass.

- [ ] **Step 3: Generalize `base.py`** — replace the whole file:

```python
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMResult:
    verdict: BaseModel  # instance of the requested response_model
    model_used: str
    tokens_used: int
    cost_usd: float


class LLMProvider(Protocol):
    def validate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout_s: float,
        response_model: type[BaseModel],
    ) -> LLMResult:
        """Call the model and return a parsed verdict + usage. Raises gateway errors."""
        ...
```

- [ ] **Step 4: Thread it through `gateway.py`** — change both method signatures and the provider calls:

```python
from pydantic import BaseModel
from app.coherence.contracts import CoherenceVerdict
```

`validate(self, *, model, system_prompt, user_prompt, today, response_model: type[BaseModel] = CoherenceVerdict)` → pass `response_model` to `self._call_with_one_retry(model, system_prompt, user_prompt, response_model)`, and `_call_with_one_retry(self, model, system_prompt, user_prompt, response_model)` passes `response_model=response_model` in BOTH provider calls.

- [ ] **Step 5: Update both providers** — in `anthropic_provider.py` and `openai_provider.py`, change the `validate` signature to

```python
    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float,
        response_model: type = None,
    ) -> LLMResult:
```

…and inside, replace `response_model=CoherenceVerdict` with `response_model=response_model or CoherenceVerdict` (keep the `CoherenceVerdict` import as fallback default).

- [ ] **Step 6: Fix the existing FakeProvider** — in `backend/tests/unit/test_gateway.py`, change `FakeProvider.validate` signature to accept `response_model=None` (add the kwarg; behavior unchanged).

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/unit tests/integration -q`
Expected: all pass (coherence pipeline untouched thanks to the default)

- [ ] **Step 8: Commit**

```bash
git add backend/app/llm_gateway backend/tests/unit/test_gateway.py
git commit -m "refactor(llm_gateway): generic response_model parameter (default CoherenceVerdict)"
```

---

## Task 7: LLM contract + citation prompts (unit, TDD)

**Files:**
- Create: `backend/app/verification/contracts.py`
- Modify: `backend/app/i18n/prompts.py`
- Test: `backend/tests/unit/test_citation_contracts.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_citation_contracts.py`

```python
import pytest
from pydantic import ValidationError

from app.constructor.node_types import NodeType
from app.i18n.prompts import CITATION_SYSTEM_PROMPT_ES, build_citation_prompt
from app.verification.contracts import CitationStyleReview, StyleIssue


def test_valid_review():
    r = CitationStyleReview(
        issues=[StyleIssue(severity="menor", code="orden_cronologico",
                           message="Ordena las citas múltiples por año.",
                           citation="(López, 2020; García, 2019)")],
        summary="Estilo APA correcto en general.",
    )
    assert r.issues[0].severity == "menor"


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        StyleIssue(severity="grave", code="x", message="y", citation=None)


def test_system_prompt_is_spanish_and_forbids_rewriting():
    assert "español" in CITATION_SYSTEM_PROMPT_ES
    assert "NUNCA" in CITATION_SYSTEM_PROMPT_ES


def test_build_citation_prompt_includes_nodes_and_citations():
    p = build_citation_prompt(
        {NodeType.problema: "Texto con (García, 2020)."},
        ["(García, 2020)"],
    )
    assert "(García, 2020)" in p
    assert "Problema" in p
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_citation_contracts.py -v`
Expected: FAIL — imports missing

- [ ] **Step 3: Implement contract** — `backend/app/verification/contracts.py`

```python
from typing import Literal

from pydantic import BaseModel

Severity = Literal["critica", "mayor", "menor"]


class StyleIssue(BaseModel):
    severity: Severity
    code: str               # snake_case corto, p.ej. "orden_cronologico"
    message: str            # en español
    citation: str | None = None


class CitationStyleReview(BaseModel):
    issues: list[StyleIssue]
    summary: str
```

- [ ] **Step 4: Add prompts** — append to `backend/app/i18n/prompts.py`:

```python
CITATION_SYSTEM_PROMPT_ES = """\
Eres un corrector experto de estilo APA 7 en español para textos académicos.
Revisas EXCLUSIVAMENTE las citas en-texto (Autor, año) que se te listan, en su
contexto. No evalúas contenido científico ni redacción general.

Busca matices que un parser no detecta, por ejemplo:
- Orden de citas múltiples dentro de un mismo paréntesis (alfabético por autor).
- Citas secundarias mal construidas ("citado en").
- Uso inconsistente de et al. entre menciones del mismo trabajo.
- Concordancia narrativa ("García (2020) afirma" vs "afirman").

Reglas:
- Reporta cada problema con severidad (critica|mayor|menor), un code corto en
  snake_case, y un message claro.
- Toda explicación va en español.
- NUNCA reescribes el texto del usuario; solo señalas problemas.
- Si todo está bien, devuelve issues=[] y un summary positivo breve.
"""


def build_citation_prompt(
    contents: dict[NodeType, str], citations: list[str]
) -> str:
    lines: list[str] = ["## Citas extraídas"]
    lines.extend(f"- {c}" for c in citations)
    lines.append("")
    lines.append("## Contexto (nodos que contienen citas)")
    for nt, text in contents.items():
        lines.append(f"### {_NODE_LABEL[nt]}\n{text}")
    lines.append("")
    lines.append("Devuelve la revisión de estilo APA estructurada.")
    return "\n".join(lines)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_citation_contracts.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/verification/contracts.py backend/app/i18n/prompts.py backend/tests/unit/test_citation_contracts.py
git commit -m "feat(verification): CitationStyleReview contract + spanish APA prompts"
```

---

## Task 8: Rate limiter + quota counting citation runs (unit, TDD)

**Files:**
- Create: `backend/app/entitlements/ratelimit.py`
- Modify: `backend/app/entitlements/quota.py`
- Test: `backend/tests/unit/test_ratelimit.py`, append to `backend/tests/integration/test_quota.py`

- [ ] **Step 1: Write the failing limiter test** — `backend/tests/unit/test_ratelimit.py`

```python
import pytest

from app.entitlements.errors import RateLimited
from app.entitlements.ratelimit import SlidingWindowLimiter


def test_allows_up_to_max():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)


def test_blocks_over_max_within_window():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)
    with pytest.raises(RateLimited):
        lim.check("p1", now=3.0)


def test_window_slides():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)
    lim.check("p1", now=61.0)  # first event expired


def test_keys_are_independent():
    lim = SlidingWindowLimiter(max_events=1, window_s=60)
    lim.check("p1", now=0.0)
    lim.check("p2", now=0.0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_ratelimit.py -v`
Expected: FAIL — module missing

- [ ] **Step 3: Implement** — `backend/app/entitlements/ratelimit.py`

```python
import time

from app.entitlements.errors import RateLimited


class SlidingWindowLimiter:
    """In-memory per-key sliding window. Single-process MVP scope."""

    def __init__(self, max_events: int, window_s: float) -> None:
        self._max = max_events
        self._window = window_s
        self._events: dict[str, list[float]] = {}

    def check(self, key: str, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        events = [e for e in self._events.get(key, []) if e > t - self._window]
        if len(events) >= self._max:
            self._events[key] = events
            raise RateLimited(f"max {self._max} events per {self._window}s")
        events.append(t)
        self._events[key] = events
```

- [ ] **Step 4: Write the failing quota test** — append to `backend/tests/integration/test_quota.py`

```python
from app.verification.models import CitationRun


@pytest.mark.asyncio
async def test_citation_llm_runs_count_toward_quota(db_session):
    # free tier: 20/month. 19 validations + 1 citation LLM run = at the cap.
    for _ in range(19):
        db_session.add(ValidationResult(node_id="n", score=80, model_used="m"))
    db_session.add(CitationRun(project_id="p", user_id="u", llm_used=True))
    await db_session.flush()
    with pytest.raises(QuotaExceeded):
        await consume_monthly_quota(db_session, user_id="u", node_ids=["n"], tier="free")
```

(Reuse the imports already present in that file; add the `CitationRun` import at the top. If `ValidationResult` is constructed differently in the existing tests, mirror that construction.)

- [ ] **Step 5: Run to verify the new quota test fails**

Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_quota.py -v`
Expected: new test FAILS (no QuotaExceeded; citation runs not counted)

- [ ] **Step 6: Count citation runs in `quota.py`** — in `consume_monthly_quota`, after computing `used`, add:

```python
    from app.verification.models import CitationRun  # local import: avoid cycles

    citation_runs = await session.scalar(
        select(func.count())
        .select_from(CitationRun)
        .where(
            CitationRun.user_id == user_id,
            CitationRun.llm_used.is_(True),
            CitationRun.created_at >= start,
        )
    )
    if (used or 0) + (citation_runs or 0) >= limit:
        raise QuotaExceeded(f"monthly quota {limit} reached for tier {tier}")
```

…replacing the existing `if (used or 0) >= limit:` block.

- [ ] **Step 7: Run to verify all pass**

Run: `cd backend && .venv/bin/python -m pytest tests/unit/test_ratelimit.py tests/integration/test_quota.py -v`
Expected: all passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/entitlements/ratelimit.py backend/app/entitlements/quota.py backend/tests/unit/test_ratelimit.py backend/tests/integration/test_quota.py
git commit -m "feat(entitlements): sliding-window limiter + citation LLM runs consume monthly quota"
```

---

## Task 9: Verification pipeline (integration, TDD, fakes)

**Files:**
- Create: `backend/app/verification/pipeline.py`
- Test: `backend/tests/integration/test_verification_pipeline.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_verification_pipeline.py`

```python
from datetime import date

import pytest

from app.auth.models import User
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import LLMTimeout
from app.verification.contracts import CitationStyleReview
from app.verification.lookup import ExistenceStatus, LookupResult
from app.verification.pipeline import verify_citations

TODAY = date(2026, 6, 11)


class FakeLookup:
    def __init__(self, status=ExistenceStatus.encontrada):
        self.calls: list[tuple[str, int]] = []
        self._status = status

    async def lookup(self, surname: str, year: int) -> LookupResult:
        self.calls.append((surname, year))
        return LookupResult(status=self._status)


class FakeGateway:
    def __init__(self, raises=None):
        self.called = False
        self._raises = raises

    def validate(self, *, model, system_prompt, user_prompt, today,
                 response_model=None):
        self.called = True
        if self._raises:
            raise self._raises
        return LLMResult(
            verdict=CitationStyleReview(issues=[], summary="Estilo correcto."),
            model_used=model, tokens_used=10, cost_usd=0.001,
        )


async def _seed(db_session, tier="pro", content="Según García (2020), hay un vacío."):
    user = User(email="t@v.com", password_hash="x", tier=tier)
    db_session.add(user)
    await db_session.flush()
    project = ResearchProject(user_id=user.id, title="T")
    db_session.add(project)
    await db_session.flush()
    for nt in DEPENDENCY_CHAIN:
        db_session.add(Node(project_id=project.id, type=nt.value,
                            content=content if nt.value == "problema" else ""))
    await db_session.commit()
    return user, project


@pytest.mark.asyncio
async def test_happy_path_pro_tier_uses_llm(db_session):
    user, project = await _seed(db_session)
    lookup, gw = FakeLookup(), FakeGateway()
    run, findings = await verify_citations(
        db_session, lookup_client=lookup, gateway=gw,
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert len(findings) == 1
    assert findings[0].surname == "García"
    assert findings[0].existence_status == "encontrada"
    assert lookup.calls == [("García", 2020)]
    assert gw.called and run.llm_used is True
    assert run.llm_summary == "Estilo correcto."


@pytest.mark.asyncio
async def test_free_tier_skips_llm(db_session):
    user, project = await _seed(db_session, tier="free")
    gw = FakeGateway()
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(), gateway=gw,
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert gw.called is False and run.llm_used is False
    assert len(findings) == 1


@pytest.mark.asyncio
async def test_llm_failure_degrades_not_aborts(db_session):
    user, project = await _seed(db_session)
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(),
        gateway=FakeGateway(raises=LLMTimeout("slow")),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert run.llm_used is False
    assert run.llm_message is not None
    assert len(findings) == 1  # deterministic part intact


@pytest.mark.asyncio
async def test_not_found_marks_possible_hallucination(db_session):
    user, project = await _seed(db_session, tier="free")
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(ExistenceStatus.no_encontrada),
        gateway=FakeGateway(), user_id=user.id, tier=user.tier,
        project_id=project.id, today=TODAY,
    )
    assert findings[0].existence_status == "no_encontrada"


@pytest.mark.asyncio
async def test_sf_citation_not_looked_up(db_session):
    user, project = await _seed(db_session, tier="free",
                                content="Lo afirma (López, s.f.).")
    lookup = FakeLookup()
    run, findings = await verify_citations(
        db_session, lookup_client=lookup, gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert lookup.calls == []
    assert findings[0].existence_status == "no_verificable"


@pytest.mark.asyncio
async def test_no_citations_project_issue(db_session):
    user, project = await _seed(db_session, tier="free", content="Sin citas aquí pero largo.")
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(), gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert findings == []
    assert any(i["code"] == "sin_citas" for i in run.project_issues)
    assert run.llm_used is False  # no citations -> no LLM even on pro


@pytest.mark.asyncio
async def test_other_users_project_raises(db_session):
    user, project = await _seed(db_session)
    with pytest.raises(LookupError):
        await verify_citations(
            db_session, lookup_client=FakeLookup(), gateway=FakeGateway(),
            user_id="someone-else", tier="pro", project_id=project.id, today=TODAY,
        )


@pytest.mark.asyncio
async def test_duplicate_citation_looked_up_once(db_session):
    user, project = await _seed(
        db_session, tier="free",
        content="García (2020) lo dijo; lo repite (García, 2020).",
    )
    lookup = FakeLookup()
    await verify_citations(
        db_session, lookup_client=lookup, gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert lookup.calls == [("García", 2020)]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_verification_pipeline.py -v`
Expected: FAIL — `app.verification.pipeline` missing

- [ ] **Step 3: Implement** — `backend/app/verification/pipeline.py`

```python
from dataclasses import asdict
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN, NodeType
from app.entitlements.errors import QuotaExceeded
from app.entitlements.quota import consume_monthly_quota
from app.entitlements.tiers import Tier, TIER_CONFIG
from app.i18n.prompts import CITATION_SYSTEM_PROMPT_ES, build_citation_prompt
from app.llm_gateway.errors import LLMError
from app.verification.apa_checks import run_apa_checks
from app.verification.contracts import CitationStyleReview
from app.verification.extraction import Citation, extract_citations
from app.verification.lookup import (
    ExistenceStatus,
    LookupClient,
    LookupResult,
    cached_lookup,
)
from app.verification.models import CitationFinding, CitationRun

LLM_TIERS = {Tier.pro, Tier.doctoral, Tier.university}


async def verify_citations(
    session: AsyncSession,
    *,
    lookup_client: LookupClient,
    gateway,
    user_id: str,
    tier: str,
    project_id: str,
    today: date,
) -> tuple[CitationRun, list[CitationFinding]]:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise LookupError("project not found")
    res = await session.scalars(select(Node).where(Node.project_id == project_id))
    nodes = {NodeType(n.type): n for n in res}

    # 1 — deterministic extraction + APA checks (free)
    citations: list[Citation] = []
    for nt in DEPENDENCY_CHAIN:
        citations.extend(extract_citations(nt, nodes[nt].content))
    issues = run_apa_checks(citations, today)
    project_issues = [asdict(i) for i in issues if i.citation_raw is None]
    by_citation: dict[str, list[dict]] = {}
    for i in issues:
        if i.citation_raw:
            by_citation.setdefault(i.citation_raw, []).append(asdict(i))

    run = CitationRun(project_id=project_id, user_id=user_id,
                      project_issues=project_issues)
    session.add(run)
    await session.flush()

    # 2 — existence lookup (free external APIs, cached, deduped per run)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    seen: dict[tuple[str, int], LookupResult] = {}
    findings: list[CitationFinding] = []
    for c in citations:
        if c.year[:4].isdigit():
            key = (c.surname, int(c.year[:4]))
            if key not in seen:
                seen[key] = await cached_lookup(
                    session, lookup_client, c.surname, key[1],
                    now=now, ttl_days=settings.lookup_cache_ttl_days,
                )
            result = seen[key]
        else:  # s.f. — sin año no hay búsqueda útil
            result = LookupResult(status=ExistenceStatus.no_verificable)
        findings.append(CitationFinding(
            run_id=run.id, node_type=c.node_type.value, raw=c.raw,
            surname=c.surname, year=c.year, narrative=c.narrative,
            format_issues=by_citation.get(c.raw, []),
            existence_status=result.status.value,
            candidates=[asdict(cd) for cd in result.candidates],
        ))
    session.add_all(findings)

    # 3 — LLM style review (paid tiers; degrades, never aborts)
    if citations and Tier(tier) in LLM_TIERS:
        try:
            await _llm_review(session, run, gateway, user_id, tier, nodes,
                              citations, today)
        except QuotaExceeded:
            run.llm_message = (
                "Cuota mensual de validaciones agotada; revisión LLM omitida."
            )
        except LLMError:
            run.llm_message = (
                "El juez de estilo no está disponible ahora; "
                "los resultados deterministas están completos."
            )

    await session.commit()
    await session.refresh(run)
    return run, findings


async def _llm_review(
    session: AsyncSession,
    run: CitationRun,
    gateway,
    user_id: str,
    tier: str,
    nodes: dict[NodeType, Node],
    citations: list[Citation],
    today: date,
) -> None:
    node_ids = await session.scalars(
        select(Node.id)
        .join(ResearchProject, ResearchProject.id == Node.project_id)
        .where(ResearchProject.user_id == user_id)
    )
    await consume_monthly_quota(session, user_id=user_id,
                                node_ids=list(node_ids), tier=tier)

    settings = get_settings()
    cfg = TIER_CONFIG[Tier(tier)]
    model = cfg.anthropic_model if settings.llm_provider == "anthropic" else cfg.openai_model
    cited_nodes = {nt for c in citations for nt in [c.node_type]}
    contents = {nt: nodes[nt].content for nt in DEPENDENCY_CHAIN if nt in cited_nodes}

    result = gateway.validate(
        model=model,
        system_prompt=CITATION_SYSTEM_PROMPT_ES,
        user_prompt=build_citation_prompt(contents, [c.raw for c in citations]),
        today=today,
        response_model=CitationStyleReview,
    )
    review: CitationStyleReview = result.verdict
    run.llm_used = True
    run.llm_summary = review.summary
    run.llm_issues = [i.model_dump() for i in review.issues]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_verification_pipeline.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/verification/pipeline.py backend/tests/integration/test_verification_pipeline.py
git commit -m "feat(verification): citation verification pipeline (extract/check/lookup/llm, degrading)"
```

---

## Task 10: HTTP endpoints + wiring (integration, TDD)

**Files:**
- Create: `backend/app/verification/schemas.py`, `backend/app/verification/service.py`, `backend/app/verification/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_verification_api.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_verification_api.py`

```python
import pytest

from app.llm_gateway.base import LLMResult
from app.main import app
from app.verification.contracts import CitationStyleReview
from app.verification.lookup import ExistenceStatus, LookupResult
from app.verification.service import get_lookup_client
from app.coherence.service import get_gateway


class FakeLookup:
    async def lookup(self, surname: str, year: int) -> LookupResult:
        return LookupResult(status=ExistenceStatus.no_encontrada)


class FakeGateway:
    def validate(self, *, model, system_prompt, user_prompt, today,
                 response_model=None):
        return LLMResult(
            verdict=CitationStyleReview(issues=[], summary="OK."),
            model_used=model, tokens_used=1, cost_usd=0.0,
        )


@pytest.fixture(autouse=True)
def _overrides():
    app.dependency_overrides[get_lookup_client] = lambda: FakeLookup()
    app.dependency_overrides[get_gateway] = lambda: FakeGateway()
    yield
    app.dependency_overrides.pop(get_lookup_client, None)
    app.dependency_overrides.pop(get_gateway, None)


async def _setup_project(client) -> tuple[dict, str]:
    await client.post("/api/auth/register",
                      json={"email": "v@w.com", "password": "pw12345"})
    tok = (await client.post(
        "/api/auth/login", json={"email": "v@w.com", "password": "pw12345"}
    )).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    pid = (await client.post("/api/projects", json={"title": "T"},
                             headers=h)).json()["id"]
    await client.put(f"/api/projects/{pid}/nodes/problema",
                     json={"content": "Lo afirma (García, 2020)."}, headers=h)
    return h, pid


@pytest.mark.asyncio
async def test_verify_citations_endpoint(client):
    h, pid = await _setup_project(client)
    r = await client.post(f"/api/projects/{pid}/verify-citations", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["findings"][0]["existence_status"] == "no_encontrada"
    assert body["findings"][0]["surname"] == "García"
    assert body["llm_used"] is False  # registered users are free tier


@pytest.mark.asyncio
async def test_latest_returns_persisted_run(client):
    h, pid = await _setup_project(client)
    await client.post(f"/api/projects/{pid}/verify-citations", headers=h)
    r = await client.get(f"/api/projects/{pid}/verify-citations/latest", headers=h)
    assert r.status_code == 200
    assert len(r.json()["findings"]) == 1


@pytest.mark.asyncio
async def test_latest_404_when_never_run(client):
    h, pid = await _setup_project(client)
    r = await client.get(f"/api/projects/{pid}/verify-citations/latest", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_other_users_project_404(client):
    h, pid = await _setup_project(client)
    await client.post("/api/auth/register",
                      json={"email": "x@y.com", "password": "pw12345"})
    tok = (await client.post(
        "/api/auth/login", json={"email": "x@y.com", "password": "pw12345"}
    )).json()["access_token"]
    r = await client.post(f"/api/projects/{pid}/verify-citations",
                          headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_requires_auth(client):
    r = await client.post("/api/projects/whatever/verify-citations")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_rate_limited_429(client, monkeypatch):
    from app.verification import router as vrouter
    from app.entitlements.ratelimit import SlidingWindowLimiter

    monkeypatch.setattr(vrouter, "_limiter",
                        SlidingWindowLimiter(max_events=1, window_s=60))
    h, pid = await _setup_project(client)
    await client.post(f"/api/projects/{pid}/verify-citations", headers=h)
    r = await client.post(f"/api/projects/{pid}/verify-citations", headers=h)
    assert r.status_code == 429
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_verification_api.py -v`
Expected: FAIL — imports missing

- [ ] **Step 3: Implement schemas** — `backend/app/verification/schemas.py`

```python
from pydantic import BaseModel


class CandidateOut(BaseModel):
    title: str
    doi: str | None
    year: int | None
    source: str


class FindingOut(BaseModel):
    node_type: str
    raw: str
    surname: str
    year: str
    narrative: bool
    format_issues: list[dict]
    existence_status: str
    candidates: list[CandidateOut]


class CitationRunOut(BaseModel):
    id: str
    created_at: str
    project_issues: list[dict]
    llm_used: bool
    llm_summary: str | None
    llm_issues: list[dict]
    llm_message: str | None
    findings: list[FindingOut]
```

- [ ] **Step 4: Implement service** — `backend/app/verification/service.py`

```python
from functools import lru_cache

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constructor.models import ResearchProject
from app.verification.lookup import CrossrefOpenAlexClient, LookupClient
from app.verification.models import CitationFinding, CitationRun


@lru_cache
def _singleton_client() -> CrossrefOpenAlexClient:
    s = get_settings()
    return CrossrefOpenAlexClient(
        httpx.AsyncClient(), mailto=s.crossref_mailto, timeout_s=s.lookup_timeout_s
    )


def get_lookup_client() -> LookupClient:
    """FastAPI dependency; overridden in tests with a fake."""
    return _singleton_client()


async def get_latest_run(
    session: AsyncSession, user_id: str, project_id: str
) -> tuple[CitationRun, list[CitationFinding]] | None:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise LookupError("project not found")
    run = await session.scalar(
        select(CitationRun)
        .where(CitationRun.project_id == project_id)
        .order_by(CitationRun.created_at.desc())
        .limit(1)
    )
    if run is None:
        return None
    findings = list(await session.scalars(
        select(CitationFinding).where(CitationFinding.run_id == run.id)
    ))
    return run, findings
```

- [ ] **Step 5: Implement router** — `backend/app/verification/router.py`

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.coherence.service import get_gateway
from app.db import get_session
from app.entitlements.errors import RateLimited
from app.entitlements.ratelimit import SlidingWindowLimiter
from app.verification import pipeline
from app.verification.models import CitationFinding, CitationRun
from app.verification.schemas import CandidateOut, CitationRunOut, FindingOut
from app.verification.service import get_latest_run, get_lookup_client

router = APIRouter(prefix="/api/projects", tags=["verification"])

_limiter = SlidingWindowLimiter(max_events=10, window_s=60.0)


def _to_out(run: CitationRun, findings: list[CitationFinding]) -> CitationRunOut:
    return CitationRunOut(
        id=run.id,
        created_at=run.created_at.isoformat(),
        project_issues=run.project_issues,
        llm_used=run.llm_used,
        llm_summary=run.llm_summary,
        llm_issues=run.llm_issues,
        llm_message=run.llm_message,
        findings=[
            FindingOut(
                node_type=f.node_type, raw=f.raw, surname=f.surname, year=f.year,
                narrative=f.narrative, format_issues=f.format_issues,
                existence_status=f.existence_status,
                candidates=[CandidateOut(**c) for c in f.candidates],
            )
            for f in findings
        ],
    )


@router.post("/{project_id}/verify-citations", response_model=CitationRunOut)
async def verify_citations(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    lookup_client=Depends(get_lookup_client),
    gateway=Depends(get_gateway),
):
    try:
        _limiter.check(project_id)
    except RateLimited:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "demasiadas verificaciones; espera un minuto")
    try:
        run, findings = await pipeline.verify_citations(
            session, lookup_client=lookup_client, gateway=gateway,
            user_id=user.id, tier=user.tier, project_id=project_id,
            today=datetime.now(timezone.utc).date(),
        )
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return _to_out(run, findings)


@router.get("/{project_id}/verify-citations/latest", response_model=CitationRunOut)
async def latest_run(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        found = await get_latest_run(session, user.id, project_id)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no runs yet")
    return _to_out(*found)
```

- [ ] **Step 6: Wire router** — in `backend/app/main.py` add:

```python
from app.verification.router import router as verification_router
app.include_router(verification_router)
```

- [ ] **Step 7: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_verification_api.py -v`
Expected: 6 passed

- [ ] **Step 8: Full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/unit tests/integration -q`
Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add backend/app/verification backend/app/main.py backend/tests/integration/test_verification_api.py
git commit -m "feat(verification): verify-citations endpoints with rate limit + injectable deps"
```

---

## Task 11: Alembic migration

**Files:**
- Create: `backend/alembic/versions/0002_citations.py`

- [ ] **Step 1: Write the migration** — `backend/alembic/versions/0002_citations.py`

```python
"""citation verification tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('citation_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('project_issues', sa.JSON(), nullable=False),
        sa.Column('llm_used', sa.Boolean(), nullable=False),
        sa.Column('llm_summary', sa.Text(), nullable=True),
        sa.Column('llm_issues', sa.JSON(), nullable=False),
        sa.Column('llm_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['research_projects.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_citation_runs_project_id'), 'citation_runs',
                    ['project_id'], unique=False)
    op.create_index(op.f('ix_citation_runs_user_id'), 'citation_runs',
                    ['user_id'], unique=False)
    op.create_index(op.f('ix_citation_runs_created_at'), 'citation_runs',
                    ['created_at'], unique=False)
    op.create_table('citation_findings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('raw', sa.String(), nullable=False),
        sa.Column('surname', sa.String(), nullable=False),
        sa.Column('year', sa.String(), nullable=False),
        sa.Column('narrative', sa.Boolean(), nullable=False),
        sa.Column('format_issues', sa.JSON(), nullable=False),
        sa.Column('existence_status', sa.String(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['citation_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_citation_findings_run_id'), 'citation_findings',
                    ['run_id'], unique=False)
    op.create_table('citation_lookups',
        sa.Column('surname_norm', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('surname_norm', 'year'),
    )


def downgrade() -> None:
    op.drop_table('citation_lookups')
    op.drop_index(op.f('ix_citation_findings_run_id'), table_name='citation_findings')
    op.drop_table('citation_findings')
    op.drop_index(op.f('ix_citation_runs_created_at'), table_name='citation_runs')
    op.drop_index(op.f('ix_citation_runs_user_id'), table_name='citation_runs')
    op.drop_index(op.f('ix_citation_runs_project_id'), table_name='citation_runs')
    op.drop_table('citation_runs')
```

- [ ] **Step 2: Verify the migration loads** (offline check; a live Postgres isn't required)

Run: `cd backend && .venv/bin/python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
cfg = Config('alembic.ini')
s = ScriptDirectory.from_config(cfg)
print([r.revision for r in s.walk_revisions()])
"`
Expected: `['0002', '0001']`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0002_citations.py
git commit -m "feat(db): migration for citation verification tables"
```

---

## Task 12: Frontend — types, client, VerificationPanel, ProjectPage

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/ProjectPage.tsx`
- Create: `frontend/src/components/VerificationPanel.tsx`

- [ ] **Step 1: Add types** — append to `frontend/src/api/types.ts`:

```typescript
export type ExistenceStatus = "encontrada" | "no_encontrada" | "no_verificable";

export interface CandidateOut {
  title: string;
  doi: string | null;
  year: number | null;
  source: string;
}

export interface FindingOut {
  node_type: NodeType;
  raw: string;
  surname: string;
  year: string;
  narrative: boolean;
  format_issues: { severity: string; code: string; message: string }[];
  existence_status: ExistenceStatus;
  candidates: CandidateOut[];
}

export interface CitationRunOut {
  id: string;
  created_at: string;
  project_issues: { severity: string; code: string; message: string }[];
  llm_used: boolean;
  llm_summary: string | null;
  llm_issues: { severity: string; code: string; message: string; citation: string | null }[];
  llm_message: string | null;
  findings: FindingOut[];
}
```

- [ ] **Step 2: Add client methods** — in `frontend/src/api/client.ts`, inside `export const api = { … }` add:

```typescript
  verifyCitations: (pid: string) =>
    req(`/projects/${pid}/verify-citations`, { method: "POST" }),
  latestCitations: (pid: string) => req(`/projects/${pid}/verify-citations/latest`),
```

- [ ] **Step 3: Create the panel** — `frontend/src/components/VerificationPanel.tsx`

```tsx
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CitationRunOut, FindingOut, NodeType } from "../api/types";
import { NODE_META, NODE_ORDER } from "../ui/nodeMeta";

const EXISTENCE_UI: Record<string, { icon: string; label: string; tone: string }> = {
  encontrada: { icon: "🟢", label: "Encontrada en la literatura", tone: "good" },
  no_encontrada: { icon: "⚠", label: "Posible cita inventada", tone: "low" },
  no_verificable: { icon: "⚪", label: "No se pudo verificar", tone: "mid" },
};

function Finding({ f }: { f: FindingOut }) {
  const ex = EXISTENCE_UI[f.existence_status];
  return (
    <li className="cite" data-tone={ex.tone}>
      <div className="cite__head">
        <code className="cite__raw">{f.raw}</code>
        <span className="cite__existence" title={ex.label}>
          {ex.icon} {ex.label}
        </span>
      </div>
      {f.format_issues.length > 0 && (
        <ul className="cite__issues">
          {f.format_issues.map((it, k) => (
            <li key={k}>
              <span className={`chip chip--${it.severity}`}>{it.severity}</span>{" "}
              {it.message}
            </li>
          ))}
        </ul>
      )}
      {f.candidates.length > 0 && (
        <ul className="cite__candidates">
          {f.candidates.map((c, k) => (
            <li key={k}>
              {c.doi ? (
                <a href={c.doi.startsWith("http") ? c.doi : `https://doi.org/${c.doi}`}
                   target="_blank" rel="noreferrer">
                  {c.title || c.doi}
                </a>
              ) : (
                c.title
              )}{" "}
              <span className="muted">({c.source})</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function VerificationPanel({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: run } = useQuery<CitationRunOut>({
    queryKey: ["citations", projectId],
    queryFn: () => api.latestCitations(projectId) as Promise<CitationRunOut>,
    retry: false,
  });

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = (await api.verifyCitations(projectId)) as CitationRunOut;
      qc.setQueryData(["citations", projectId], r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo verificar.");
    } finally {
      setBusy(false);
    }
  };

  const byNode = new Map<NodeType, FindingOut[]>();
  for (const f of run?.findings ?? []) {
    byNode.set(f.node_type, [...(byNode.get(f.node_type) ?? []), f]);
  }

  return (
    <section className="card verif">
      <header className="verif__head">
        <div>
          <h3>Verificación de citas</h3>
          <p className="node__hint">
            Formato APA-7 y existencia en Crossref/OpenAlex (anti-alucinación).
          </p>
        </div>
        <button className="btn" onClick={onRun} disabled={busy}>
          {busy ? "Verificando…" : "Verificar citas"}
        </button>
      </header>

      {error && <p className="vp vp--warn">⚠ {error}</p>}

      {run && (
        <div className="verif__body">
          {run.project_issues.map((i, k) => (
            <p key={k} className="muted">ℹ {i.message}</p>
          ))}

          {NODE_ORDER.filter((nt) => byNode.has(nt)).map((nt) => (
            <div key={nt} className="verif__group">
              <p className="field-label">{NODE_META[nt].label}</p>
              <ul className="verif__list">
                {byNode.get(nt)!.map((f, k) => <Finding key={k} f={f} />)}
              </ul>
            </div>
          ))}

          {run.llm_message && <p className="muted">ℹ {run.llm_message}</p>}
          {run.llm_used && (
            <div className="verif__llm">
              <p className="field-label">Revisión de estilo (IA)</p>
              {run.llm_summary && <p>{run.llm_summary}</p>}
              {run.llm_issues.length > 0 && (
                <ul className="cite__issues">
                  {run.llm_issues.map((it, k) => (
                    <li key={k}>
                      <span className={`chip chip--${it.severity}`}>{it.severity}</span>{" "}
                      {it.message} {it.citation && <code>{it.citation}</code>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Mount it in ProjectPage** — in `frontend/src/pages/ProjectPage.tsx`:
  - add `import { VerificationPanel } from "../components/VerificationPanel";`
  - after the closing `</div>` of `<div className="spine">…</div>`, add:

```tsx
        <VerificationPanel projectId={id} />
```

- [ ] **Step 5: Minimal styles** — append to `frontend/src/index.css`:

```css
/* ---- Verificación de citas ---- */
.verif { margin-top: 2.5rem; padding: 1.5rem; }
.verif__head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.verif__body { margin-top: 1rem; display: grid; gap: 1rem; }
.verif__list { list-style: none; padding: 0; display: grid; gap: .6rem; }
.cite { border: 1px solid var(--line, #e5e7eb); border-radius: 10px; padding: .7rem .9rem; }
.cite[data-tone="low"] { border-color: #f59e0b; }
.cite__head { display: flex; justify-content: space-between; gap: .8rem; flex-wrap: wrap; }
.cite__raw { font-size: .9em; }
.cite__existence { font-size: .85em; white-space: nowrap; }
.cite__issues, .cite__candidates { margin: .5rem 0 0; padding-left: 1rem; font-size: .9em; }
.verif__llm { border-top: 1px dashed var(--line, #e5e7eb); padding-top: .8rem; }
```

(If `index.css` defines different variable names for borders, reuse those instead of `--line`.)

- [ ] **Step 6: Build**

Run: `cd frontend && npm run build`
Expected: builds clean, no TS errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/components/VerificationPanel.tsx frontend/src/pages/ProjectPage.tsx frontend/src/index.css
git commit -m "feat(frontend): citation verification panel with existence + APA badges"
```

---

## Task 13: Evals — golden citations vs live APIs (NOT in CI)

**Files:**
- Create: `backend/tests/evals/citation_golden.py`, `backend/tests/evals/run_citation_evals.py`

- [ ] **Step 1: Golden dataset** — `backend/tests/evals/citation_golden.py`

```python
"""Citas doradas para evaluar el lookup contra las APIs vivas. NO corre en CI."""

# (surname, year, expected_status) — reales famosas vs inventadas
GOLDEN_CITATIONS: list[tuple[str, int, str]] = [
    ("Bandura", 1977, "encontrada"),      # Self-efficacy
    ("Hattie", 2009, "encontrada"),       # Visible Learning
    ("Creswell", 2014, "encontrada"),     # Research Design
    ("Vygotsky", 1978, "encontrada"),     # Mind in Society
    ("Kuhn", 1962, "encontrada"),         # Structure of Scientific Revolutions
    ("Zzyzwiczak", 2019, "no_encontrada"),
    ("Quetzalfuegoz", 2021, "no_encontrada"),
    ("Brzemyslawski", 2015, "no_encontrada"),
]
```

- [ ] **Step 2: Runner** — `backend/tests/evals/run_citation_evals.py`

```python
"""Run: .venv/bin/python -m tests.evals.run_citation_evals   (desde backend/)
Golpea Crossref/OpenAlex reales. NO corre en CI."""
import asyncio

import httpx

from app.config import get_settings
from app.verification.lookup import CrossrefOpenAlexClient
from tests.evals.citation_golden import GOLDEN_CITATIONS


async def main() -> None:
    s = get_settings()
    client = CrossrefOpenAlexClient(
        httpx.AsyncClient(), mailto=s.crossref_mailto, timeout_s=s.lookup_timeout_s
    )
    hits = 0
    for surname, year, expected in GOLDEN_CITATIONS:
        r = await client.lookup(surname, year)
        ok = r.status.value == expected
        hits += ok
        print(f"{'✓' if ok else '✗'} {surname} ({year}): {r.status.value} "
              f"(esperado {expected})")
    total = len(GOLDEN_CITATIONS)
    print(f"\n{hits}/{total} correctos ({hits / total:.0%})")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Confirm it is excluded from CI** — CI runs `pytest tests/unit tests/integration`; these files contain no `test_` functions collected by pytest. Run the deterministic suite to confirm nothing new is collected:

Run: `cd backend && .venv/bin/python -m pytest tests/unit tests/integration -q`
Expected: same pass count as Task 10, no network access.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/evals/citation_golden.py backend/tests/evals/run_citation_evals.py
git commit -m "test(evals): golden citation lookup evals against live APIs (excluded from CI)"
```

---

## Task 14: Final verification + spec touch-up

- [ ] **Step 1: Full backend suite + frontend build**

Run: `cd backend && .venv/bin/python -m pytest tests/unit tests/integration -q && cd ../frontend && npm run build`
Expected: all tests pass; build clean.

- [ ] **Step 2: Fix the spec's stale rate-limit sentence** — in `docs/superpowers/specs/2026-06-11-velvyko-citation-verification-design.md` §5, replace "reutiliza el rate-limit por proyecto existente (10 ejecuciones/min)" with "se añade un limitador en memoria por proyecto (10 ejecuciones/min, `entitlements/ratelimit.py`)" — the MVP never implemented a limiter, only the `RateLimited` exception.

- [ ] **Step 3: Update README** — add a short "Verificación de citas (Fase 2)" bullet to the feature list and the two new endpoints to the API section (follow the existing format).

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-11-velvyko-citation-verification-design.md README.md
git commit -m "docs: fase 2 spec rate-limit correction + README endpoints"
```

---

## Self-review notes

- **Spec coverage:** §3 extracción → Task 2 · §4 checks → Task 3 · §5 lookup/caché/fail-closed → Task 5 · §6 LLM híbrido tier-gated + cuota + degradación → Tasks 6–9 · §7 modelos/API/migración → Tasks 4, 10, 11 · §8 frontend → Task 12 · §9 testing/evals → en cada task + Task 13 · §10 config → Task 1. Rate-limit (§5) → Task 8 + corrección del spec en Task 14.
- **Consistency:** `LookupResult.candidates` es `list[Candidate]`; en DB se guarda como `list[dict]` vía `asdict`. `gateway.validate(..., response_model=)` default `CoherenceVerdict` mantiene intactos coherence y sus fakes.
