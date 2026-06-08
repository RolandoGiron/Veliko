import pytest

from app.coherence.contracts import CoherenceVerdict
from app.coherence.service import get_gateway
from app.llm_gateway.base import LLMResult
from app.main import app


class FakeGateway:
    def validate(self, *, model, system_prompt, user_prompt, today):
        return LLMResult(
            verdict=CoherenceVerdict(score=92, issues=[], suggestions=["mejora x"], summary="bien"),
            model_used=model, tokens_used=10, cost_usd=0.001,
        )


@pytest.fixture(autouse=True)
def _fake_gateway():
    app.dependency_overrides[get_gateway] = lambda: FakeGateway()
    yield
    app.dependency_overrides.pop(get_gateway, None)


async def _auth(client):
    await client.post("/api/auth/register", json={"email": "z@z.com", "password": "pw12345"})
    r = await client.post("/api/auth/login", json={"email": "z@z.com", "password": "pw12345"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_validate_endpoint_returns_verdict(client):
    h = await _auth(client)
    pid = (await client.post("/api/projects", json={"title": "T"}, headers=h)).json()["id"]
    await client.put(
        f"/api/projects/{pid}/nodes/problema",
        json={"content": " ".join(["palabra"] * 40)}, headers=h,
    )
    r = await client.post(f"/api/projects/{pid}/nodes/problema/validate", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "validated"
    assert body["score"] == 92
    assert body["node_state"] == "valido"
    assert body["blocked"] is False
