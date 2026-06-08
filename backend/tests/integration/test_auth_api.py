import pytest


@pytest.mark.asyncio
async def test_register_then_login_then_me(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "a@b.com", "password": "pw12345"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "a@b.com"
    assert r.json()["tier"] == "free"

    r = await client.post(
        "/api/auth/login", json={"email": "a@b.com", "password": "pw12345"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    await client.post(
        "/api/auth/register", json={"email": "c@d.com", "password": "right-pw"}
    )
    r = await client.post(
        "/api/auth/login", json={"email": "c@d.com", "password": "wrong-pw"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
