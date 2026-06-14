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
        target = set(normalize_surname(surname).split())
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

    async def _crossref(
        self, surname: str, year: int, target: set[str]
    ) -> list[Candidate]:
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
            if not any(
                target <= set(normalize_surname(f).split()) for f in families if f
            ):
                continue
            title = (item.get("title") or [""])[0]
            out.append(Candidate(title=title, doi=item.get("DOI"), year=year,
                                 source="crossref"))
        return out

    async def _openalex(
        self, surname: str, year: int, target: set[str]
    ) -> list[Candidate]:
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
            if not target <= tokens:
                continue
            doi = item.get("doi")
            if doi:
                doi = doi.removeprefix("https://doi.org/")
            out.append(Candidate(title=item.get("title") or "", doi=doi,
                                 year=year, source="openalex"))
        return out


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _row_to_result(row: CitationLookup) -> LookupResult:
    return LookupResult(
        status=ExistenceStatus(row.status),
        candidates=[Candidate(**c) for c in row.candidates],
    )


async def cached_lookup(
    session: AsyncSession,
    client: LookupClient,
    surname: str,
    year: int,
    *,
    now: datetime,
    ttl_days: int,
) -> LookupResult:
    now = _as_aware(now)
    key = normalize_surname(surname)
    row = await session.get(CitationLookup, {"surname_norm": key, "year": year})
    if row is not None and _as_aware(row.fetched_at) >= now - timedelta(days=ttl_days):
        return _row_to_result(row)
    result = await client.lookup(surname, year)
    if result.status is ExistenceStatus.no_verificable:
        # Stale-on-failure: existence does not expire, so honor a prior cached
        # match when both upstream sources are unreachable.
        return _row_to_result(row) if row is not None else result
    if row is None:
        row = CitationLookup(surname_norm=key, year=year)
        session.add(row)
    row.status = result.status.value
    row.candidates = [asdict(c) for c in result.candidates]
    row.fetched_at = now
    await session.flush()
    return result
