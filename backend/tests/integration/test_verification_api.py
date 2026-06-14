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
