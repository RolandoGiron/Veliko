import pytest


async def _auth_headers(client) -> dict[str, str]:
    await client.post(
        "/api/auth/register", json={"email": "u@v.com", "password": "pw12345"}
    )
    r = await client.post(
        "/api/auth/login", json={"email": "u@v.com", "password": "pw12345"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_project_seeds_six_empty_nodes(client):
    h = await _auth_headers(client)
    r = await client.post("/api/projects", json={"title": "Tesis X"}, headers=h)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = await client.get(f"/api/projects/{pid}", headers=h)
    nodes = r.json()["nodes"]
    assert [n["type"] for n in nodes] == [
        "problema", "objetivos", "hipotesis", "variables", "metodologia", "instrumentos"
    ]
    assert all(n["state"] == "sin_validar" for n in nodes)
    assert all(n["content"] == "" for n in nodes)


@pytest.mark.asyncio
async def test_edit_node_marks_self_and_descendants_obsoleto_only_after_validation(client):
    h = await _auth_headers(client)
    pid = (await client.post("/api/projects", json={"title": "T"}, headers=h)).json()["id"]

    r = await client.put(
        f"/api/projects/{pid}/nodes/problema",
        json={"content": "Un problema de investigacion claramente delimitado."},
        headers=h,
    )
    assert r.status_code == 200
    # without any validation, editing keeps it 'sin_validar' (never validated yet)
    nodes = {n["type"]: n for n in (await client.get(f"/api/projects/{pid}", headers=h)).json()["nodes"]}
    assert nodes["problema"]["state"] == "sin_validar"


@pytest.mark.asyncio
async def test_cannot_access_other_users_project(client):
    h1 = await _auth_headers(client)
    pid = (await client.post("/api/projects", json={"title": "T"}, headers=h1)).json()["id"]

    await client.post("/api/auth/register", json={"email": "x@y.com", "password": "pw12345"})
    tok = (await client.post("/api/auth/login", json={"email": "x@y.com", "password": "pw12345"})).json()["access_token"]
    h2 = {"Authorization": f"Bearer {tok}"}

    r = await client.get(f"/api/projects/{pid}", headers=h2)
    assert r.status_code == 404
