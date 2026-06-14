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
    # Fix 3: OpenAlex DOI normalized to bare form, matching Crossref.
    assert all(c.doi == "10.1037/0033-295x.84.2.191" for c in r.candidates)


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


async def test_openalex_compound_surname_matches():
    body = {"results": [{
        "title": "Obra",
        "doi": None,
        "authorships": [{"author": {"display_name": "Ana García López"}}],
    }]}

    def handler(req: httpx.Request) -> httpx.Response:
        if "crossref" in req.url.host:
            return httpx.Response(200, json=EMPTY_CROSSREF)
        return httpx.Response(200, json=body)

    r = await _client(handler).lookup("García López", 2020)
    assert r.status == ExistenceStatus.encontrada


async def test_lookup_truncates_to_three_candidates():
    body = {"message": {"items": [
        {"title": [t], "DOI": str(i), "author": [{"family": "Bandura"}]}
        for i, t in enumerate("ABCD")
    ]}}

    def handler(req: httpx.Request) -> httpx.Response:
        if "crossref" in req.url.host:
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=EMPTY_OPENALEX)

    r = await _client(handler).lookup("Bandura", 1977)
    assert len(r.candidates) == 3


async def test_cached_lookup_stale_on_failure(db_session):
    """An expired row + client returning no_verificable serves the stale data:
    existence does not expire, so a prior positive match is honored on outage."""

    class Failing:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            return LookupResult(status=ExistenceStatus.no_verificable)

    now = datetime.now(timezone.utc)
    db_session.add(CitationLookup(
        surname_norm="bandura", year=1977, status="encontrada",
        candidates=[{"title": "t", "doi": "d", "year": 1977, "source": "crossref"}],
        fetched_at=now - timedelta(days=31),
    ))
    await db_session.flush()

    r = await cached_lookup(db_session, Failing(), "Bandura", 1977, now=now, ttl_days=30)
    assert r.status == ExistenceStatus.encontrada
    assert r.candidates[0].doi == "d"


async def test_cached_lookup_stale_negative_not_resurfaced(db_session):
    """An expired no_encontrada row must NOT be resurfaced on outage: during a
    full outage we return no_verificable rather than implying 'posible inventada'."""

    class Failing:
        async def lookup(self, surname: str, year: int) -> LookupResult:
            return LookupResult(status=ExistenceStatus.no_verificable)

    now = datetime.now(timezone.utc)
    db_session.add(CitationLookup(
        surname_norm="zzyzwicz", year=2019, status="no_encontrada", candidates=[],
        fetched_at=now - timedelta(days=31),
    ))
    await db_session.flush()

    r = await cached_lookup(db_session, Failing(), "Zzyzwicz", 2019, now=now, ttl_days=30)
    assert r.status == ExistenceStatus.no_verificable
