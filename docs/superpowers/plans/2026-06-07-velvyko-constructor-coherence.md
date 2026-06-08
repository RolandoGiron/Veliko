# Velvyko — Constructor + Coherence Engine (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the demonstrable Velvyko MVP — a research project with 6 methodological nodes the user writes, plus an on-demand Scientific Coherence Engine (LLM-judge with structured output, hash-based cascade freshness, advisor/strict gating by tier, cost guardrails, fail-closed errors).

**Architecture:** Modular monolith deployed as Docker containers onto the **existing shared 8 GB VPS** (`srv1533829`, 72.60.126.116), alongside a running production stack (n8n, evolution-api/WhatsApp, a clinic Postgres, Traefik, Redis). React (Vite) SPA served as static files; Python + FastAPI backend with clean module boundaries (`auth`, `entitlements`, `constructor`, `coherence`, `llm_gateway`, `i18n`); a **dedicated** Velvyko Postgres container (`pgvector/pgvector:pg16`, DB `velvyko`) for storage — isolated from the clinic DB. TLS + routing via the **existing Traefik** (host-mode, Docker provider, Let's Encrypt) using container labels; **no Caddy in production**. The `llm_gateway` is the only module that knows the AI provider and abstracts Anthropic + OpenAI behind one interface. Everything orchestrates a 5-step validation pipeline that avoids the paid LLM call whenever possible.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) + Alembic · Pydantic v2 + pydantic-settings · `instructor` · `anthropic` + `openai` SDKs · `passlib[bcrypt]` + `pyjwt` · pytest + pytest-asyncio + httpx · Postgres 16 + pgvector · React + Vite + TypeScript + TanStack Query · Docker Compose · Traefik (existing, via labels) · Caddy (local dev only).

---

## Infrastructure — VERIFIED on the VPS (2026-06-08)

These are not assumptions; they were confirmed by inspecting the running host via shell/Docker and the Hostinger + n8n MCPs.

| Item | Verified reality | Impact on plan |
|---|---|---|
| VPS | id `1533829`, `srv1533829.hstgr.cloud`, 8 GB / 2 vCPU / 100 GB, Ubuntu 24.04 + Docker | Shared, **not dedicated**. ~3.2–3.6 GB already used by prod stack → budget ~1–1.5 GB for Velvyko. CPU ~2.5%, disk 30/100 GB — ample. |
| Reverse proxy | **Traefik** (`traefik-traefik-1`), `network_mode: host`, `--providers.docker --providers.docker.exposedbydefault=false`, Let's Encrypt HTTP-challenge, ACME email `admin@srv1533829.hstgr.cloud` | Route Velvyko via **Traefik labels**, not Caddy. Reaches container bridge IP via Docker socket. |
| Domain pattern | existing routers use `<sub>.srv1533829.hstgr.cloud` (`admin.`, `wa.`, `n8n-dlyc.`) | Velvyko gets `velvyko.srv1533829.hstgr.cloud` (override later with a real domain). |
| Shared Docker network | **`clinic-net`** (external bridge, `name: clinic-net`) — clinic-postgres, evolution, n8n all attached | Velvyko backend joins `clinic-net` so Traefik can route to it. The plan's earlier `postgres_default` guess was **wrong**. |
| Existing Postgres | `clinic-postgres` = `postgres:16-alpine` (16.13), user `clinic`, db `clinic_crm`/`evolution_api`, `max_connections=50`, **pgvector NOT installed**, owned by the clinic stack | **Do not reuse.** Run a dedicated `pgvector/pgvector:pg16` container for Velvyko (data isolation + pgvector available for the future `memory` module). |
| Redis | `hg-redis` published on host `:6379`, reachable at `host.docker.internal:6379` (host-gateway) | Available if a future module needs it; MVP does not. |
| n8n | `n8n-dlyc` running, reachable via MCP; has Schedule Trigger + HTTP Request + Postgres nodes; already runs prod workflows | "n8n-scheduled evals" assumption **valid**. Build the eval workflow via the n8n MCP, namespaced `velvyko-evals`. n8n can reach Velvyko's backend over `clinic-net`. |

---

## Configuration Defaults (resolves spec §11)

These are concrete, tunable defaults that live in `backend/app/config.py` (overridable by env vars). They are real values, not placeholders.

| Setting | Value | Notes |
|---|---|---|
| LLM providers | `anthropic` + `openai`, default `anthropic` | `LLM_PROVIDER` env switches the active one |
| Model — free/pro | `claude-haiku-4-5-20251001` / `gpt-4o-mini` | volume tier |
| Model — doctoral/university | `claude-sonnet-4-6` / `gpt-4o` | strict/deep tier |
| Monthly validation quota | free=20, pro=200, doctoral=1000, university=5000 | per user |
| Per-project rate limit | 10 validations / minute | anti-abuse |
| Daily global kill switch | `$20.00` USD/day | pauses paid validations + alerts |
| Strict-mode block threshold | score `< 70` blocks (doctoral only) | advisor never blocks |
| Min words (pre-check) | problema=30, objetivos=15, hipotesis=10, variables=10, metodologia=30, instrumentos=15 | per node type |
| Circuit breaker | open after 5 consecutive failures, pause 60 s | in `llm_gateway` |
| LLM timeout / retries | 30 s, 1 retry w/ backoff (transport) + instructor `max_retries=2` (schema) | |
| Auth | custom JWT, HS256, 7-day access token | `JWT_SECRET` env |

---

## File Structure

```
backend/
  pyproject.toml
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    __init__.py
    main.py                  # FastAPI app + router includes + lifespan
    config.py                # Settings (pydantic-settings)
    db.py                    # async engine, session factory, Base, get_session dep
    auth/
      __init__.py
      models.py              # User
      security.py            # hash_password, verify_password, create_token, decode_token
      schemas.py             # RegisterIn, LoginIn, TokenOut, UserOut
      service.py             # register_user, authenticate_user
      deps.py                # get_current_user
      router.py              # POST /api/auth/register|login, GET /api/auth/me
    entitlements/
      __init__.py
      tiers.py               # Tier enum, TIER_CONFIG
      gate.py                # apply_gate(verdict, tier) -> GateResult
      quota.py               # MonthlyQuota + RateLimiter checks
      errors.py              # QuotaExceeded, RateLimited
    constructor/
      __init__.py
      node_types.py          # NodeType, DEPENDENCY_CHAIN, upstream_types()
      models.py              # ResearchProject, Node
      hashing.py             # compute_node_hash(node_type, contents)
      freshness.py           # Freshness enum, compute_state()
      schemas.py             # ProjectIn/Out, NodeIn/Out, NodeState
      service.py             # create_project, list_projects, upsert_node, get_graph
      router.py              # /api/projects ...
    coherence/
      __init__.py
      contracts.py           # Issue, CoherenceVerdict (Pydantic, the LLM contract)
      prechecks.py           # run_prechecks(...) -> PrecheckResult
      models.py              # ValidationResult
      pipeline.py            # validate_node(...) 5-step orchestration
      schemas.py             # ValidationOut
      service.py             # thin service wiring deps
      router.py              # POST /api/projects/{pid}/nodes/{type}/validate
    llm_gateway/
      __init__.py
      base.py                # LLMResult, LLMProvider Protocol
      errors.py              # LLMTimeout, LLMRateLimit, LLMUnavailable, LLMUnparseable, BudgetExceeded
      budget.py              # DailyBudget tracker
      breaker.py             # CircuitBreaker
      providers/
        __init__.py
        anthropic_provider.py
        openai_provider.py
      gateway.py             # LLMGateway: select provider, instructor, retries, breaker, budget, cost
    i18n/
      __init__.py
      prompts.py             # SYSTEM_PROMPT_ES (rubric), build_user_prompt()
  tests/
    __init__.py
    conftest.py              # async db fixture, app client, fake gateway
    unit/
      test_hashing.py
      test_freshness.py
      test_prechecks.py
      test_gate.py
      test_quota.py
      test_budget.py
      test_breaker.py
      test_security.py
    integration/
      test_auth_api.py
      test_constructor_api.py
      test_pipeline.py       # 5-step pipeline w/ FAKE gateway, all failure modes, idempotency
    evals/
      golden_dataset.py      # ~20-50 cases
      run_evals.py           # NOT in CI; manual / n8n-scheduled
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    api/client.ts            # fetch wrapper + auth header
    api/types.ts             # mirrors backend schemas
    auth/AuthContext.tsx
    pages/LoginPage.tsx
    pages/ProjectsPage.tsx
    pages/ProjectPage.tsx    # the 6-node constructor
    components/NodeEditor.tsx
    components/FreshnessBadge.tsx
    components/ValidationPanel.tsx
docker-compose.yml            # dedicated velvyko-postgres + Traefik labels on clinic-net
Caddyfile                     # local dev only (prod uses existing Traefik)
.env.example
README.md
```

---

## Task 0: Prerequisites & environment setup

**No app code.** Infra unknowns are already RESOLVED (see "Infrastructure — VERIFIED" above). This task records the deployment decisions and prepares the env template. The dedicated Postgres container itself is created in Task 24 (deployment); for **local dev** any Postgres 16 works.

Architecture decisions (locked, from verified inspection):
- **Postgres:** dedicated container `velvyko-postgres` (`pgvector/pgvector:pg16`), **not** the shared `clinic-postgres`. Own volume, own credentials. pgvector ships in the image → no separate install.
- **Proxy:** existing **Traefik** via container labels. No Caddy in prod. Velvyko backend joins the external `clinic-net` network so Traefik (host-mode, Docker provider) can route to it.
- **Public host:** `velvyko.srv1533829.hstgr.cloud` (Traefik + Let's Encrypt auto-cert). Swap to a real domain by changing one env var.

- [ ] **Step 1: (Optional) re-confirm the host state**

If revisiting later, re-verify nothing drifted:
```bash
docker network ls | grep clinic-net                 # external shared net exists
docker inspect traefik-traefik-1 --format '{{.HostConfig.NetworkMode}}'   # -> host
docker ps --format '{{.Names}}\t{{.Image}}' | grep -E 'postgres|traefik|n8n'
```
Expected: `clinic-net` present, Traefik in `host` mode. (pgvector is **not** in the clinic Postgres — that's why Velvyko ships its own.)

- [ ] **Step 2: Pick the public hostname & confirm DNS**

Velvyko will be served at `velvyko.srv1533829.hstgr.cloud`. The `*.srv1533829.hstgr.cloud` wildcard already resolves to the VPS (existing subdomains work), so no DNS change is needed for the MVP. Record the chosen host in `.env` as `VELVYKO_HOST`.

- [ ] **Step 3: Create `.env.example` (committed) and real `.env` (gitignored)**

Create `.env.example`:
```bash
# --- Database (DEDICATED Velvyko Postgres, pgvector/pgvector:pg16) ---
# In prod, host is the compose service name `velvyko-postgres` on clinic-net.
DATABASE_URL=postgresql+asyncpg://velvyko:CHANGE_ME@velvyko-postgres:5432/velvyko
POSTGRES_USER=velvyko
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=velvyko
# --- Routing (existing Traefik) ---
VELVYKO_HOST=velvyko.srv1533829.hstgr.cloud
# --- Auth ---
JWT_SECRET=CHANGE_ME_64_RANDOM_HEX
JWT_EXPIRE_DAYS=7
# --- LLM ---
LLM_PROVIDER=anthropic            # anthropic | openai
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
# --- Guardrails ---
DAILY_BUDGET_USD=20
```
Generate real secrets for `.env`:
```bash
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
```
> Local dev: point `DATABASE_URL` at `localhost:5432` (or run `pgvector/pgvector:pg16` locally). The MVP defines no vector columns (YAGNI), so pgvector is dormant until the future `memory` module — but the image has it ready.

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "chore: env template and verified infra decisions for velvyko"
```

---

## Task 1: Backend scaffold — pyproject, config, db, app

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "velvyko-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "passlib[bcrypt]>=1.7",
    "pyjwt>=2.8",
    "instructor>=1.3",
    "anthropic>=0.39",
    "openai>=1.40",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "aiosqlite>=0.20",   # in-memory async db for tests
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `backend/app/config.py`**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://velvyko:velvyko@localhost:5432/velvyko"

    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    llm_provider: str = "anthropic"           # anthropic | openai
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    daily_budget_usd: float = 20.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown_s: int = 60
    llm_timeout_s: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Create `backend/app/db.py`**

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(_settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

- [ ] **Step 4: Create `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Velvyko API")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Create `backend/tests/conftest.py`**

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, get_session
from app.main import app

# Import all models so Base.metadata is fully populated for create_all.
import app.auth.models  # noqa: F401
import app.constructor.models  # noqa: F401
import app.coherence.models  # noqa: F401


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

> Note: the model imports in `conftest.py` reference files created in later tasks. Until those exist, run only the specific unit tests that don't import the app (Tasks 4–12 pure-logic tests). The `client` fixture is first exercised in Task 2.

- [ ] **Step 6: Install and verify health**

```bash
cd backend && pip install -e ".[dev]"
python -c "from app.main import app; print('import ok')"
```
Expected: `import ok` (the model-import lines in conftest are not loaded by this command).

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/app/db.py backend/app/main.py backend/tests/__init__.py backend/tests/conftest.py
git commit -m "feat(backend): scaffold FastAPI app, settings, async db, test harness"
```

---

## Task 2: Auth — password hashing & JWT (unit, TDD)

**Files:**
- Create: `backend/app/auth/__init__.py`, `backend/app/auth/security.py`, `backend/tests/unit/test_security.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/unit/test_security.py`:
```python
import pytest

from app.auth import security


def test_password_hash_roundtrip():
    h = security.hash_password("s3cret-pw")
    assert h != "s3cret-pw"
    assert security.verify_password("s3cret-pw", h) is True
    assert security.verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token = security.create_access_token(subject="user-123")
    assert security.decode_access_token(token) == "user-123"


def test_jwt_rejects_tampered_token():
    token = security.create_access_token(subject="user-123")
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token + "x")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError: app.auth.security`.

- [ ] **Step 3: Implement `backend/app/auth/security.py`** (also create empty `backend/app/auth/__init__.py`)

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()


class InvalidToken(Exception):
    pass


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=_settings.jwt_expire_days),
    }
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    return payload["sub"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_security.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/__init__.py backend/app/auth/security.py backend/tests/unit/test_security.py
git commit -m "feat(auth): password hashing and JWT helpers"
```

---

## Task 3: Auth — User model, service, router (integration, TDD)

**Files:**
- Create: `backend/app/auth/models.py`, `backend/app/auth/schemas.py`, `backend/app/auth/service.py`, `backend/app/auth/deps.py`, `backend/app/auth/router.py`, `backend/tests/integration/__init__.py`, `backend/tests/integration/test_auth_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/integration/test_auth_api.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/integration/test_auth_api.py -v`
Expected: FAIL — 404 on `/api/auth/register` (routes not wired).

- [ ] **Step 3: Implement the model** — `backend/app/auth/models.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[str] = mapped_column(String, nullable=False, default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Implement schemas** — `backend/app/auth/schemas.py`

```python
from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    tier: str
```

- [ ] **Step 5: Implement service** — `backend/app/auth/service.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.auth.models import User


class EmailTaken(Exception):
    pass


class BadCredentials(Exception):
    pass


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailTaken(email)
    user = User(email=email, password_hash=security.hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not security.verify_password(password, user.password_hash):
        raise BadCredentials()
    return user
```

- [ ] **Step 6: Implement the current-user dependency** — `backend/app/auth/deps.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.auth.models import User
from app.db import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        user_id = security.decode_access_token(creds.credentials)
    except security.InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return user
```

- [ ] **Step 7: Implement router** — `backend/app/auth/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security, service
from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    try:
        user = await service.register_user(session, body.email, body.password)
    except service.EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    return UserOut(id=user.id, email=user.email, tier=user.tier)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    try:
        user = await service.authenticate_user(session, body.email, body.password)
    except service.BadCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    return TokenOut(access_token=security.create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, tier=user.tier)
```

- [ ] **Step 8: Wire router into the app** — modify `backend/app/main.py`

```python
from fastapi import FastAPI

from app.auth.router import router as auth_router

app = FastAPI(title="Velvyko API")
app.include_router(auth_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 9: Run to verify it passes**

Run: `cd backend && pytest tests/integration/test_auth_api.py tests/unit/test_security.py -v`
Expected: all passed.

- [ ] **Step 10: Commit**

```bash
git add backend/app/auth backend/tests/integration/__init__.py backend/tests/integration/test_auth_api.py backend/app/main.py
git commit -m "feat(auth): user model, register/login/me endpoints with JWT"
```

---

## Task 4: Constructor — node types & dependency chain (unit, TDD)

**Files:**
- Create: `backend/app/constructor/__init__.py`, `backend/app/constructor/node_types.py`, `backend/tests/unit/__init__.py`, `backend/tests/unit/test_node_types.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_node_types.py`

```python
from app.constructor.node_types import (
    DEPENDENCY_CHAIN,
    NodeType,
    upstream_types,
)


def test_chain_order():
    assert DEPENDENCY_CHAIN == [
        NodeType.problema,
        NodeType.objetivos,
        NodeType.hipotesis,
        NodeType.variables,
        NodeType.metodologia,
        NodeType.instrumentos,
    ]


def test_upstream_of_root_is_empty():
    assert upstream_types(NodeType.problema) == []


def test_upstream_is_all_preceding_in_order():
    assert upstream_types(NodeType.hipotesis) == [
        NodeType.problema,
        NodeType.objetivos,
    ]
    assert upstream_types(NodeType.instrumentos) == [
        NodeType.problema,
        NodeType.objetivos,
        NodeType.hipotesis,
        NodeType.variables,
        NodeType.metodologia,
    ]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_node_types.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/constructor/node_types.py` (and empty `backend/app/constructor/__init__.py`, `backend/tests/unit/__init__.py`)

```python
from enum import StrEnum


class NodeType(StrEnum):
    problema = "problema"
    objetivos = "objetivos"
    hipotesis = "hipotesis"
    variables = "variables"
    metodologia = "metodologia"
    instrumentos = "instrumentos"


DEPENDENCY_CHAIN: list[NodeType] = [
    NodeType.problema,
    NodeType.objetivos,
    NodeType.hipotesis,
    NodeType.variables,
    NodeType.metodologia,
    NodeType.instrumentos,
]

# Minimum word count per node type for the deterministic pre-check (spec §11 default).
MIN_WORDS: dict[NodeType, int] = {
    NodeType.problema: 30,
    NodeType.objetivos: 15,
    NodeType.hipotesis: 10,
    NodeType.variables: 10,
    NodeType.metodologia: 30,
    NodeType.instrumentos: 15,
}


def upstream_types(node_type: NodeType) -> list[NodeType]:
    """All node types preceding `node_type` in the dependency chain, in order."""
    idx = DEPENDENCY_CHAIN.index(node_type)
    return DEPENDENCY_CHAIN[:idx]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_node_types.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/constructor/__init__.py backend/app/constructor/node_types.py backend/tests/unit/__init__.py backend/tests/unit/test_node_types.py
git commit -m "feat(constructor): node types and dependency chain"
```

---

## Task 5: Constructor — content hashing (unit, TDD)

**Files:**
- Create: `backend/app/constructor/hashing.py`, `backend/tests/unit/test_hashing.py`

The hash must include the node's own content **plus the content of every upstream node, in chain order**, so that editing any upstream node changes the hash of all descendants (cascade).

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_hashing.py`

```python
from app.constructor.hashing import compute_node_hash
from app.constructor.node_types import NodeType


def test_hash_is_deterministic():
    contents = {NodeType.problema: "el problema", NodeType.objetivos: "los objetivos"}
    h1 = compute_node_hash(NodeType.objetivos, contents)
    h2 = compute_node_hash(NodeType.objetivos, contents)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_hash_changes_when_own_content_changes():
    base = {NodeType.problema: "P", NodeType.objetivos: "O1"}
    changed = {NodeType.problema: "P", NodeType.objetivos: "O2"}
    assert compute_node_hash(NodeType.objetivos, base) != compute_node_hash(
        NodeType.objetivos, changed
    )


def test_hash_changes_when_upstream_changes():
    base = {NodeType.problema: "P1", NodeType.objetivos: "O"}
    changed = {NodeType.problema: "P2", NodeType.objetivos: "O"}
    # editing the upstream `problema` must invalidate downstream `objetivos`
    assert compute_node_hash(NodeType.objetivos, base) != compute_node_hash(
        NodeType.objetivos, changed
    )


def test_root_hash_ignores_other_nodes():
    a = {NodeType.problema: "P", NodeType.objetivos: "O1"}
    b = {NodeType.problema: "P", NodeType.objetivos: "O2"}
    # problema has no upstream; downstream edits must NOT change its hash
    assert compute_node_hash(NodeType.problema, a) == compute_node_hash(
        NodeType.problema, b
    )


def test_missing_upstream_content_treated_as_empty():
    contents = {NodeType.objetivos: "O"}  # problema absent
    # must not raise; absent upstream contributes empty string
    assert len(compute_node_hash(NodeType.objetivos, contents)) == 64
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_hashing.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/constructor/hashing.py`

```python
import hashlib

from app.constructor.node_types import NodeType, upstream_types


def compute_node_hash(node_type: NodeType, contents: dict[NodeType, str]) -> str:
    """sha256 over upstream contents (in chain order) + own content.

    `contents` maps node type -> current content. Missing entries count as "".
    """
    parts: list[str] = []
    for dep in upstream_types(node_type):
        parts.append(f"{dep.value}:{contents.get(dep, '')}")
    parts.append(f"{node_type.value}:{contents.get(node_type, '')}")
    joined = "\x1e".join(parts)  # record separator, unlikely in content
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_hashing.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/constructor/hashing.py backend/tests/unit/test_hashing.py
git commit -m "feat(constructor): content+upstream hashing for cascade freshness"
```

---

## Task 6: Constructor — freshness state (unit, TDD)

**Files:**
- Create: `backend/app/constructor/freshness.py`, `backend/tests/unit/test_freshness.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_freshness.py`

```python
from app.constructor.freshness import Freshness, compute_state


def test_never_validated_is_sin_validar():
    assert compute_state(current_hash="abc", last_validated_hash=None) == (
        Freshness.sin_validar
    )


def test_matching_hash_is_valido():
    assert compute_state(current_hash="abc", last_validated_hash="abc") == (
        Freshness.valido
    )


def test_differing_hash_is_obsoleto():
    assert compute_state(current_hash="abc", last_validated_hash="xyz") == (
        Freshness.obsoleto
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_freshness.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/constructor/freshness.py`

```python
from enum import StrEnum


class Freshness(StrEnum):
    sin_validar = "sin_validar"   # ⚪
    valido = "valido"             # 🟢
    obsoleto = "obsoleto"         # 🟡


def compute_state(current_hash: str, last_validated_hash: str | None) -> Freshness:
    if last_validated_hash is None:
        return Freshness.sin_validar
    if current_hash == last_validated_hash:
        return Freshness.valido
    return Freshness.obsoleto
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_freshness.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/constructor/freshness.py backend/tests/unit/test_freshness.py
git commit -m "feat(constructor): 3-state freshness computation"
```

---

## Task 7: Constructor — models, schemas, service, router (integration, TDD)

**Files:**
- Create: `backend/app/constructor/models.py`, `backend/app/constructor/schemas.py`, `backend/app/constructor/service.py`, `backend/app/constructor/router.py`, `backend/tests/integration/test_constructor_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_constructor_api.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/integration/test_constructor_api.py -v`
Expected: FAIL — 404 (routes missing).

- [ ] **Step 3: Implement models** — `backend/app/constructor/models.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (UniqueConstraint("project_id", "type", name="uq_node_project_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("research_projects.id"), index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    last_validated_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
```

- [ ] **Step 4: Implement schemas** — `backend/app/constructor/schemas.py`

```python
from pydantic import BaseModel


class ProjectIn(BaseModel):
    title: str
    language: str = "es"


class NodeOut(BaseModel):
    type: str
    content: str
    state: str  # Freshness value


class ProjectSummary(BaseModel):
    id: str
    title: str
    language: str


class ProjectDetail(ProjectSummary):
    nodes: list[NodeOut]


class NodeIn(BaseModel):
    content: str
```

- [ ] **Step 5: Implement service** — `backend/app/constructor/service.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constructor.freshness import compute_state
from app.constructor.hashing import compute_node_hash
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN, NodeType


class ProjectNotFound(Exception):
    pass


async def create_project(
    session: AsyncSession, user_id: str, title: str, language: str
) -> ResearchProject:
    project = ResearchProject(user_id=user_id, title=title, language=language)
    session.add(project)
    await session.flush()
    for nt in DEPENDENCY_CHAIN:
        session.add(Node(project_id=project.id, type=nt.value, content=""))
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession, user_id: str) -> list[ResearchProject]:
    res = await session.scalars(
        select(ResearchProject).where(ResearchProject.user_id == user_id)
    )
    return list(res)


async def _get_owned_project(
    session: AsyncSession, user_id: str, project_id: str
) -> ResearchProject:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise ProjectNotFound(project_id)
    return project


async def _nodes_by_type(session: AsyncSession, project_id: str) -> dict[NodeType, Node]:
    res = await session.scalars(select(Node).where(Node.project_id == project_id))
    return {NodeType(n.type): n for n in res}


async def get_graph(
    session: AsyncSession, user_id: str, project_id: str
) -> tuple[ResearchProject, list[tuple[Node, str]]]:
    project = await _get_owned_project(session, user_id, project_id)
    nodes = await _nodes_by_type(session, project_id)
    contents = {nt: n.content for nt, n in nodes.items()}
    ordered: list[tuple[Node, str]] = []
    for nt in DEPENDENCY_CHAIN:
        node = nodes[nt]
        state = compute_state(
            compute_node_hash(nt, contents), node.last_validated_hash
        )
        ordered.append((node, state.value))
    return project, ordered


async def upsert_node_content(
    session: AsyncSession, user_id: str, project_id: str, node_type: NodeType, content: str
) -> Node:
    await _get_owned_project(session, user_id, project_id)
    node = await session.scalar(
        select(Node).where(Node.project_id == project_id, Node.type == node_type.value)
    )
    if node is None:
        raise ProjectNotFound(project_id)
    node.content = content
    await session.commit()
    await session.refresh(node)
    return node
```

- [ ] **Step 6: Implement router** — `backend/app/constructor/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.constructor import service
from app.constructor.node_types import NodeType
from app.constructor.schemas import (
    NodeIn,
    NodeOut,
    ProjectDetail,
    ProjectIn,
    ProjectSummary,
)
from app.db import get_session

router = APIRouter(prefix="/api/projects", tags=["constructor"])


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    p = await service.create_project(session, user.id, body.title, body.language)
    return ProjectSummary(id=p.id, title=p.title, language=p.language)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return [
        ProjectSummary(id=p.id, title=p.title, language=p.language)
        for p in await service.list_projects(session, user.id)
    ]


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        project, nodes = await service.get_graph(session, user.id, project_id)
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return ProjectDetail(
        id=project.id,
        title=project.title,
        language=project.language,
        nodes=[NodeOut(type=n.type, content=n.content, state=state) for n, state in nodes],
    )


@router.put("/{project_id}/nodes/{node_type}", response_model=NodeOut)
async def update_node(
    project_id: str,
    node_type: NodeType,
    body: NodeIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        node = await service.upsert_node_content(
            session, user.id, project_id, node_type, body.content
        )
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    # recompute single-node state for the response
    _, nodes = await service.get_graph(session, user.id, project_id)
    state = next(s for n, s in nodes if n.type == node_type.value)
    return NodeOut(type=node.type, content=node.content, state=state)
```

- [ ] **Step 7: Wire router** — add to `backend/app/main.py`

```python
from app.constructor.router import router as constructor_router
# ...
app.include_router(constructor_router)
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd backend && pytest tests/integration/test_constructor_api.py -v`
Expected: all passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/constructor/models.py backend/app/constructor/schemas.py backend/app/constructor/service.py backend/app/constructor/router.py backend/tests/integration/test_constructor_api.py backend/app/main.py
git commit -m "feat(constructor): projects + 6-node graph with freshness states"
```

---

## Task 8: Coherence — the Pydantic LLM contract (unit, TDD)

**Files:**
- Create: `backend/app/coherence/__init__.py`, `backend/app/coherence/contracts.py`, `backend/tests/unit/test_contracts.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_contracts.py`

```python
import pytest
from pydantic import ValidationError

from app.coherence.contracts import CoherenceVerdict, Issue


def test_valid_verdict():
    v = CoherenceVerdict(
        score=80,
        issues=[
            Issue(
                severity="mayor",
                dimension="falsabilidad",
                explanation="La hipotesis no es falsable.",
                location=None,
            )
        ],
        suggestions=["Reformular como prediccion contrastable."],
        summary="Coherente pero con una hipotesis debil.",
    )
    assert v.score == 80
    assert v.issues[0].dimension == "falsabilidad"


def test_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        CoherenceVerdict(score=120, issues=[], suggestions=[], summary="x")


def test_invalid_dimension_rejected():
    with pytest.raises(ValidationError):
        Issue(severity="mayor", dimension="inventada", explanation="x", location=None)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_contracts.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/coherence/contracts.py` (and empty `backend/app/coherence/__init__.py`)

```python
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critica", "mayor", "menor"]
Dimension = Literal[
    "coherencia", "falsabilidad", "claridad", "alineacion_objetivos", "medibilidad"
]


class Issue(BaseModel):
    severity: Severity
    dimension: Dimension
    explanation: str            # en español
    location: str | None = None


class CoherenceVerdict(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: list[Issue]
    suggestions: list[str]      # mejoras; NUNCA reescribe el contenido (D5)
    summary: str
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_contracts.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/coherence/__init__.py backend/app/coherence/contracts.py backend/tests/unit/test_contracts.py
git commit -m "feat(coherence): Pydantic CoherenceVerdict contract"
```

---

## Task 9: Coherence — deterministic pre-checks (unit, TDD)

**Files:**
- Create: `backend/app/coherence/prechecks.py`, `backend/tests/unit/test_prechecks.py`

Pre-checks short-circuit the pipeline **before** any LLM call: empty content, too short, or any upstream dependency not currently `valido`.

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_prechecks.py`

```python
from app.coherence.prechecks import PrecheckCode, run_prechecks
from app.constructor.freshness import Freshness
from app.constructor.node_types import NodeType


def test_empty_content_blocks():
    r = run_prechecks(NodeType.problema, "   ", upstream_states={})
    assert r.ok is False
    assert r.code == PrecheckCode.empty


def test_too_short_blocks():
    r = run_prechecks(NodeType.problema, "tres palabras solas", upstream_states={})
    assert r.ok is False
    assert r.code == PrecheckCode.too_short


def test_unvalidated_upstream_blocks():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(
        NodeType.hipotesis,
        long,
        upstream_states={
            NodeType.problema: Freshness.valido,
            NodeType.objetivos: Freshness.obsoleto,
        },
    )
    assert r.ok is False
    assert r.code == PrecheckCode.upstream_not_valid


def test_passes_when_long_enough_and_upstream_valid():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(
        NodeType.hipotesis,
        long,
        upstream_states={
            NodeType.problema: Freshness.valido,
            NodeType.objetivos: Freshness.valido,
        },
    )
    assert r.ok is True
    assert r.code is None


def test_root_node_passes_without_upstream():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(NodeType.problema, long, upstream_states={})
    assert r.ok is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_prechecks.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/coherence/prechecks.py`

```python
from dataclasses import dataclass
from enum import StrEnum

from app.constructor.freshness import Freshness
from app.constructor.node_types import MIN_WORDS, NodeType, upstream_types


class PrecheckCode(StrEnum):
    empty = "empty"
    too_short = "too_short"
    upstream_not_valid = "upstream_not_valid"


@dataclass(frozen=True)
class PrecheckResult:
    ok: bool
    code: PrecheckCode | None = None
    message: str | None = None


def run_prechecks(
    node_type: NodeType,
    content: str,
    upstream_states: dict[NodeType, Freshness],
) -> PrecheckResult:
    stripped = content.strip()
    if not stripped:
        return PrecheckResult(False, PrecheckCode.empty, "El nodo está vacío.")

    if len(stripped.split()) < MIN_WORDS[node_type]:
        return PrecheckResult(
            False,
            PrecheckCode.too_short,
            f"Necesita al menos {MIN_WORDS[node_type]} palabras para validar.",
        )

    for dep in upstream_types(node_type):
        if upstream_states.get(dep) != Freshness.valido:
            return PrecheckResult(
                False,
                PrecheckCode.upstream_not_valid,
                f"Primero valida '{dep.value}': de él depende este nodo.",
            )

    return PrecheckResult(True)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_prechecks.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/coherence/prechecks.py backend/tests/unit/test_prechecks.py
git commit -m "feat(coherence): deterministic pre-checks (empty/short/upstream)"
```

---

## Task 10: Entitlements — tiers, gate, quota (unit, TDD)

**Files:**
- Create: `backend/app/entitlements/__init__.py`, `backend/app/entitlements/tiers.py`, `backend/app/entitlements/gate.py`, `backend/app/entitlements/errors.py`, `backend/tests/unit/test_gate.py`

(Quota persistence is tested in the pipeline integration task; here we cover the pure gate + tier config.)

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_gate.py`

```python
from app.coherence.contracts import CoherenceVerdict
from app.entitlements.gate import apply_gate
from app.entitlements.tiers import Tier, TIER_CONFIG


def _verdict(score: int) -> CoherenceVerdict:
    return CoherenceVerdict(score=score, issues=[], suggestions=[], summary="s")


def test_advisor_never_blocks_even_low_score():
    g = apply_gate(_verdict(10), Tier.free)
    assert g.blocked is False
    assert g.mode == "asesor"


def test_doctoral_strict_blocks_below_threshold():
    g = apply_gate(_verdict(50), Tier.doctoral)
    assert g.mode == "estricto"
    assert g.blocked is True


def test_doctoral_strict_allows_at_or_above_threshold():
    g = apply_gate(_verdict(70), Tier.doctoral)
    assert g.blocked is False


def test_every_tier_has_models_and_quota():
    for tier in Tier:
        cfg = TIER_CONFIG[tier]
        assert cfg.monthly_quota > 0
        assert cfg.anthropic_model
        assert cfg.openai_model
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_gate.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement tiers** — `backend/app/entitlements/tiers.py` (and empty `__init__.py`)

```python
from dataclasses import dataclass
from enum import StrEnum


class Tier(StrEnum):
    free = "free"
    pro = "pro"
    doctoral = "doctoral"
    university = "university"


@dataclass(frozen=True)
class TierConfig:
    monthly_quota: int
    anthropic_model: str
    openai_model: str
    strict: bool
    strict_threshold: int  # block if score < threshold (strict only)


_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"
_GPT_MINI = "gpt-4o-mini"
_GPT = "gpt-4o"

TIER_CONFIG: dict[Tier, TierConfig] = {
    Tier.free: TierConfig(20, _HAIKU, _GPT_MINI, strict=False, strict_threshold=70),
    Tier.pro: TierConfig(200, _HAIKU, _GPT_MINI, strict=False, strict_threshold=70),
    Tier.doctoral: TierConfig(1000, _SONNET, _GPT, strict=True, strict_threshold=70),
    Tier.university: TierConfig(5000, _SONNET, _GPT, strict=False, strict_threshold=70),
}
```

- [ ] **Step 4: Implement gate** — `backend/app/entitlements/gate.py`

```python
from dataclasses import dataclass

from app.coherence.contracts import CoherenceVerdict
from app.entitlements.tiers import Tier, TIER_CONFIG


@dataclass(frozen=True)
class GateResult:
    mode: str          # "asesor" | "estricto"
    blocked: bool


def apply_gate(verdict: CoherenceVerdict, tier: Tier) -> GateResult:
    cfg = TIER_CONFIG[tier]
    if not cfg.strict:
        return GateResult(mode="asesor", blocked=False)
    return GateResult(mode="estricto", blocked=verdict.score < cfg.strict_threshold)
```

- [ ] **Step 5: Implement errors** — `backend/app/entitlements/errors.py`

```python
class QuotaExceeded(Exception):
    pass


class RateLimited(Exception):
    pass
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_gate.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/entitlements backend/tests/unit/test_gate.py
git commit -m "feat(entitlements): tier config + advisor/strict gate"
```

---

## Task 11: LLM gateway — daily budget kill switch (unit, TDD)

**Files:**
- Create: `backend/app/llm_gateway/__init__.py`, `backend/app/llm_gateway/budget.py`, `backend/app/llm_gateway/errors.py`, `backend/tests/unit/test_budget.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_budget.py`

```python
from datetime import date

import pytest

from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.errors import BudgetExceeded


def test_under_budget_allows():
    b = DailyBudget(limit_usd=1.0)
    b.ensure_within_budget(today=date(2026, 6, 7))  # no spend yet
    b.record(0.40, today=date(2026, 6, 7))
    b.ensure_within_budget(today=date(2026, 6, 7))


def test_over_budget_blocks():
    b = DailyBudget(limit_usd=1.0)
    b.record(1.20, today=date(2026, 6, 7))
    with pytest.raises(BudgetExceeded):
        b.ensure_within_budget(today=date(2026, 6, 7))


def test_budget_resets_next_day():
    b = DailyBudget(limit_usd=1.0)
    b.record(1.20, today=date(2026, 6, 7))
    # new day -> spend resets, allowed again
    b.ensure_within_budget(today=date(2026, 6, 8))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_budget.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement errors** — `backend/app/llm_gateway/errors.py` (and empty `__init__.py`)

```python
class LLMError(Exception):
    """Base for all gateway failures."""


class LLMTimeout(LLMError):
    pass


class LLMRateLimit(LLMError):
    pass


class LLMUnavailable(LLMError):
    """Provider 5xx / circuit breaker open."""


class LLMUnparseable(LLMError):
    """Model never produced a valid CoherenceVerdict."""


class BudgetExceeded(LLMError):
    pass
```

- [ ] **Step 4: Implement budget** — `backend/app/llm_gateway/budget.py`

```python
from datetime import date

from app.llm_gateway.errors import BudgetExceeded


class DailyBudget:
    """In-process daily spend tracker / kill switch.

    Single-process MVP. If the backend later runs multiple workers, move this
    counter to Postgres or Redis. The interface stays identical.
    """

    def __init__(self, limit_usd: float) -> None:
        self._limit = limit_usd
        self._day: date | None = None
        self._spent = 0.0

    def _roll(self, today: date) -> None:
        if self._day != today:
            self._day = today
            self._spent = 0.0

    def ensure_within_budget(self, today: date) -> None:
        self._roll(today)
        if self._spent >= self._limit:
            raise BudgetExceeded(f"daily budget {self._limit} reached")

    def record(self, cost_usd: float, today: date) -> None:
        self._roll(today)
        self._spent += cost_usd
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_budget.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/llm_gateway/__init__.py backend/app/llm_gateway/budget.py backend/app/llm_gateway/errors.py backend/tests/unit/test_budget.py
git commit -m "feat(llm_gateway): daily budget kill switch + error taxonomy"
```

---

## Task 12: LLM gateway — circuit breaker (unit, TDD)

**Files:**
- Create: `backend/app/llm_gateway/breaker.py`, `backend/tests/unit/test_breaker.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_breaker.py`

```python
import pytest

from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import LLMUnavailable


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(threshold=3, cooldown_s=60)
    for _ in range(3):
        cb.record_failure(now=0.0)
    with pytest.raises(LLMUnavailable):
        cb.ensure_closed(now=1.0)


def test_success_resets_failures():
    cb = CircuitBreaker(threshold=3, cooldown_s=60)
    cb.record_failure(now=0.0)
    cb.record_failure(now=0.0)
    cb.record_success()
    cb.record_failure(now=0.0)
    cb.ensure_closed(now=1.0)  # only 1 failure since reset -> still closed


def test_closes_again_after_cooldown():
    cb = CircuitBreaker(threshold=2, cooldown_s=60)
    cb.record_failure(now=0.0)
    cb.record_failure(now=0.0)
    with pytest.raises(LLMUnavailable):
        cb.ensure_closed(now=10.0)
    cb.ensure_closed(now=61.0)  # cooldown elapsed -> allowed (half-open)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_breaker.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/llm_gateway/breaker.py`

```python
from app.llm_gateway.errors import LLMUnavailable


class CircuitBreaker:
    def __init__(self, threshold: int, cooldown_s: float) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_s
        self._failures = 0
        self._opened_at: float | None = None

    def ensure_closed(self, now: float) -> None:
        if self._opened_at is None:
            return
        if now - self._opened_at >= self._cooldown:
            # half-open: allow a trial call, keep counters until it resolves
            return
        raise LLMUnavailable("circuit open")

    def record_failure(self, now: float) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = now

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_breaker.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm_gateway/breaker.py backend/tests/unit/test_breaker.py
git commit -m "feat(llm_gateway): circuit breaker"
```

---

## Task 13: i18n — prompts (unit, TDD)

**Files:**
- Create: `backend/app/i18n/__init__.py`, `backend/app/i18n/prompts.py`, `backend/tests/unit/test_prompts.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_prompts.py`

```python
from app.constructor.node_types import NodeType
from app.i18n.prompts import SYSTEM_PROMPT_ES, build_user_prompt


def test_system_prompt_mentions_rubric_dimensions():
    for dim in ("coherencia", "falsabilidad", "claridad", "alineacion_objetivos", "medibilidad"):
        assert dim in SYSTEM_PROMPT_ES


def test_user_prompt_includes_content_and_upstream():
    prompt = build_user_prompt(
        node_type=NodeType.hipotesis,
        content="Mi hipotesis.",
        upstream={NodeType.problema: "El problema.", NodeType.objetivos: "Los objetivos."},
    )
    assert "hipotesis" in prompt
    assert "Mi hipotesis." in prompt
    assert "El problema." in prompt
    assert "Los objetivos." in prompt


def test_user_prompt_for_root_has_no_upstream_section():
    prompt = build_user_prompt(node_type=NodeType.problema, content="P", upstream={})
    assert "P" in prompt
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_prompts.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/i18n/prompts.py` (and empty `__init__.py`)

```python
from app.constructor.node_types import NodeType

# Static, long, cacheable system prompt (prompt caching pays only the variable part).
SYSTEM_PROMPT_ES = """\
Eres un examinador metodológico riguroso de tesis científicas de posgrado.
Tu trabajo NO es redactar contenido: es evaluar la coherencia científica del
texto que te dan, a la luz de sus dependencias aguas arriba, y devolver un
veredicto estructurado.

Evalúa estrictamente estas cinco dimensiones:
- coherencia: consistencia interna y con los nodos previos.
- falsabilidad: si aplica, ¿la afirmación es contrastable/refutable?
- claridad: precisión conceptual, ausencia de ambigüedad.
- alineacion_objetivos: ¿responde a y se alinea con los nodos previos?
- medibilidad: ¿los constructos son observables/medibles donde corresponde?

Reglas:
- Puntúa de 0 a 100 (rigor de jurado doctoral).
- Reporta cada problema con severidad (critica|mayor|menor) y dimensión.
- En 'suggestions' propones mejoras, pero NUNCA reescribes el contenido del usuario.
- Toda explicación y sugerencia va en español.
- Si no puedes evaluar con confianza, sé conservador en el score; no inventes.
"""

_NODE_LABEL = {
    NodeType.problema: "Problema de investigación",
    NodeType.objetivos: "Objetivos",
    NodeType.hipotesis: "Hipótesis",
    NodeType.variables: "Variables",
    NodeType.metodologia: "Metodología",
    NodeType.instrumentos: "Instrumentos",
}


def build_user_prompt(
    node_type: NodeType, content: str, upstream: dict[NodeType, str]
) -> str:
    lines: list[str] = []
    if upstream:
        lines.append("## Dependencias aguas arriba (ya validadas)")
        for dep, text in upstream.items():
            lines.append(f"### {_NODE_LABEL[dep]}\n{text}")
        lines.append("")
    lines.append(f"## Nodo a evaluar: {_NODE_LABEL[node_type]} (tipo: {node_type.value})")
    lines.append(content)
    lines.append("")
    lines.append("Devuelve el veredicto estructurado para ESTE nodo.")
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_prompts.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/i18n backend/tests/unit/test_prompts.py
git commit -m "feat(i18n): Spanish rubric system prompt + user prompt builder"
```

---

## Task 14: LLM gateway — provider protocol & implementations

**Files:**
- Create: `backend/app/llm_gateway/base.py`, `backend/app/llm_gateway/providers/__init__.py`, `backend/app/llm_gateway/providers/anthropic_provider.py`, `backend/app/llm_gateway/providers/openai_provider.py`

These wrap `instructor`-patched SDK clients. They are exercised by **evals** (Task 20), never by CI (no real network in tests). No unit test here — the contract is enforced by the `LLMProvider` Protocol and the gateway tests in Task 15 use a fake.

- [ ] **Step 1: Implement the protocol & result type** — `backend/app/llm_gateway/base.py`

```python
from dataclasses import dataclass
from typing import Protocol

from app.coherence.contracts import CoherenceVerdict


@dataclass(frozen=True)
class LLMResult:
    verdict: CoherenceVerdict
    model_used: str
    tokens_used: int
    cost_usd: float


class LLMProvider(Protocol):
    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float
    ) -> LLMResult:
        """Call the model and return a parsed verdict + usage. Raises gateway errors."""
        ...
```

- [ ] **Step 2: Implement the Anthropic provider** — `backend/app/llm_gateway/providers/anthropic_provider.py`

```python
import anthropic
import instructor

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import (
    LLMRateLimit,
    LLMTimeout,
    LLMUnavailable,
    LLMUnparseable,
)

# USD per 1M tokens (approx; tune from billing). input/output blended is fine for MVP.
_PRICES = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
}


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _PRICES.get(model, (3.0, 15.0))
    return (in_tok * pin + out_tok * pout) / 1_000_000


class AnthropicProvider:
    def __init__(self, api_key: str) -> None:
        self._client = instructor.from_anthropic(anthropic.Anthropic(api_key=api_key))

    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float
    ) -> LLMResult:
        try:
            verdict, completion = self._client.chat.completions.create_with_completion(
                model=model,
                max_tokens=1500,
                system=[{"type": "text", "text": system_prompt,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_prompt}],
                response_model=CoherenceVerdict,
                max_retries=2,
                timeout=timeout_s,
            )
        except anthropic.APITimeoutError as e:
            raise LLMTimeout(str(e)) from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimit(str(e)) from e
        except anthropic.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailable(str(e)) from e
            raise
        except instructor.exceptions.InstructorRetryException as e:
            raise LLMUnparseable(str(e)) from e

        usage = completion.usage
        in_tok = getattr(usage, "input_tokens", 0)
        out_tok = getattr(usage, "output_tokens", 0)
        return LLMResult(
            verdict=verdict,
            model_used=model,
            tokens_used=in_tok + out_tok,
            cost_usd=_cost(model, in_tok, out_tok),
        )
```

- [ ] **Step 3: Implement the OpenAI provider** — `backend/app/llm_gateway/providers/openai_provider.py`

```python
import instructor
import openai

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import (
    LLMRateLimit,
    LLMTimeout,
    LLMUnavailable,
    LLMUnparseable,
)

_PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
}


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _PRICES.get(model, (2.50, 10.0))
    return (in_tok * pin + out_tok * pout) / 1_000_000


class OpenAIProvider:
    def __init__(self, api_key: str) -> None:
        self._client = instructor.from_openai(openai.OpenAI(api_key=api_key))

    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float
    ) -> LLMResult:
        try:
            verdict, completion = self._client.chat.completions.create_with_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=CoherenceVerdict,
                max_retries=2,
                timeout=timeout_s,
            )
        except openai.APITimeoutError as e:
            raise LLMTimeout(str(e)) from e
        except openai.RateLimitError as e:
            raise LLMRateLimit(str(e)) from e
        except openai.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailable(str(e)) from e
            raise
        except instructor.exceptions.InstructorRetryException as e:
            raise LLMUnparseable(str(e)) from e

        usage = completion.usage
        in_tok = getattr(usage, "prompt_tokens", 0)
        out_tok = getattr(usage, "completion_tokens", 0)
        return LLMResult(
            verdict=verdict,
            model_used=model,
            tokens_used=in_tok + out_tok,
            cost_usd=_cost(model, in_tok, out_tok),
        )
```

- [ ] **Step 4: Verify imports** (no network)

Run: `cd backend && python -c "from app.llm_gateway.providers.anthropic_provider import AnthropicProvider; from app.llm_gateway.providers.openai_provider import OpenAIProvider; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm_gateway/base.py backend/app/llm_gateway/providers
git commit -m "feat(llm_gateway): Anthropic + OpenAI providers via instructor"
```

---

## Task 15: LLM gateway — orchestrator (unit, TDD with fakes)

**Files:**
- Create: `backend/app/llm_gateway/gateway.py`, `backend/tests/unit/test_gateway.py`

The gateway selects the provider/model, enforces the breaker and budget, performs one transport retry on timeout, records cost, and translates results. It accepts an injected provider so it is testable without network.

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/test_gateway.py`

```python
from datetime import date

import pytest

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import BudgetExceeded, LLMTimeout, LLMUnavailable
from app.llm_gateway.gateway import LLMGateway


class FakeProvider:
    def __init__(self, *, raises=None, calls_to_fail=0):
        self.calls = 0
        self._raises = raises
        self._calls_to_fail = calls_to_fail

    def validate(self, *, model, system_prompt, user_prompt, timeout_s):
        self.calls += 1
        if self._raises and self.calls <= self._calls_to_fail:
            raise self._raises
        return LLMResult(
            verdict=CoherenceVerdict(score=88, issues=[], suggestions=[], summary="ok"),
            model_used=model,
            tokens_used=100,
            cost_usd=0.01,
        )


def _gateway(provider, *, budget=10.0, threshold=5):
    return LLMGateway(
        provider=provider,
        budget=DailyBudget(limit_usd=budget),
        breaker=CircuitBreaker(threshold=threshold, cooldown_s=60),
        timeout_s=30.0,
    )


def test_happy_path_returns_result_and_records_cost():
    p = FakeProvider()
    gw = _gateway(p)
    res = gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert res.verdict.score == 88
    assert p.calls == 1


def test_timeout_retries_once_then_succeeds():
    p = FakeProvider(raises=LLMTimeout("slow"), calls_to_fail=1)
    gw = _gateway(p)
    res = gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert res.verdict.score == 88
    assert p.calls == 2  # one failed, one retry succeeded


def test_timeout_twice_raises():
    p = FakeProvider(raises=LLMTimeout("slow"), calls_to_fail=2)
    gw = _gateway(p)
    with pytest.raises(LLMTimeout):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))


def test_budget_blocks_before_calling_provider():
    p = FakeProvider()
    gw = _gateway(p, budget=0.0)
    with pytest.raises(BudgetExceeded):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert p.calls == 0


def test_breaker_opens_after_repeated_unavailable():
    p = FakeProvider(raises=LLMUnavailable("5xx"), calls_to_fail=99)
    gw = _gateway(p, threshold=2)
    for _ in range(2):
        with pytest.raises(LLMUnavailable):
            gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    calls_before = p.calls
    with pytest.raises(LLMUnavailable):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert p.calls == calls_before  # breaker open -> provider not called
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/unit/test_gateway.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** — `backend/app/llm_gateway/gateway.py`

```python
import time
from datetime import date

from app.llm_gateway.base import LLMProvider, LLMResult
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import LLMTimeout, LLMUnavailable


class LLMGateway:
    def __init__(
        self,
        provider: LLMProvider,
        budget: DailyBudget,
        breaker: CircuitBreaker,
        timeout_s: float,
    ) -> None:
        self._provider = provider
        self._budget = budget
        self._breaker = breaker
        self._timeout_s = timeout_s

    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, today: date
    ) -> LLMResult:
        self._budget.ensure_within_budget(today)
        self._breaker.ensure_closed(now=time.monotonic())

        try:
            result = self._call_with_one_retry(model, system_prompt, user_prompt)
        except (LLMUnavailable, LLMTimeout):
            self._breaker.record_failure(now=time.monotonic())
            raise

        self._breaker.record_success()
        self._budget.record(result.cost_usd, today)
        return result

    def _call_with_one_retry(
        self, model: str, system_prompt: str, user_prompt: str
    ) -> LLMResult:
        try:
            return self._provider.validate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_s=self._timeout_s,
            )
        except LLMTimeout:
            time.sleep(0.5)  # simple backoff; one retry
            return self._provider.validate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_s=self._timeout_s,
            )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/unit/test_gateway.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm_gateway/gateway.py backend/tests/unit/test_gateway.py
git commit -m "feat(llm_gateway): orchestrator with retry, breaker, budget, cost"
```

---

## Task 16: Coherence — ValidationResult model & quota persistence

**Files:**
- Create: `backend/app/coherence/models.py`, `backend/app/entitlements/quota.py`, `backend/tests/integration/test_quota.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_quota.py`

```python
import pytest
from datetime import datetime, timezone

from app.coherence.models import ValidationResult
from app.entitlements.errors import QuotaExceeded
from app.entitlements.quota import consume_monthly_quota


@pytest.mark.asyncio
async def test_quota_counts_this_month_and_blocks_over_limit(db_session):
    # tier free => limit 20; insert 20 results this month
    now = datetime.now(timezone.utc)
    for _ in range(20):
        db_session.add(
            ValidationResult(
                node_id="n", score=80, issues=[], suggestions=[],
                model_used="m", tokens_used=1, cost_usd=0.0, created_at=now,
            )
        )
    await db_session.commit()

    with pytest.raises(QuotaExceeded):
        await consume_monthly_quota(db_session, user_id="u", node_ids=["n"], tier="free")


@pytest.mark.asyncio
async def test_quota_allows_when_under_limit(db_session):
    # no prior results -> allowed
    await consume_monthly_quota(db_session, user_id="u", node_ids=["n"], tier="free")
```

> The quota counts `ValidationResult` rows whose `node_id` belongs to the user's nodes in the current calendar month. For the unit-style integration test we pass the user's `node_ids` explicitly; the pipeline (Task 17) resolves them from the user's projects.

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/integration/test_quota.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement the model** — `backend/app/coherence/models.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("nodes.id"), index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    model_used: Mapped[str] = mapped_column(String, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
```

- [ ] **Step 4: Implement quota** — `backend/app/entitlements/quota.py`

```python
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coherence.models import ValidationResult
from app.entitlements.errors import QuotaExceeded
from app.entitlements.tiers import Tier, TIER_CONFIG


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def consume_monthly_quota(
    session: AsyncSession, user_id: str, node_ids: list[str], tier: str
) -> None:
    """Raise QuotaExceeded if the user already hit their monthly validation cap.

    `node_ids` are all node ids owned by the user (the rows that count toward quota).
    Call this BEFORE the paid LLM call.
    """
    limit = TIER_CONFIG[Tier(tier)].monthly_quota
    if not node_ids:
        return
    start = _month_start(datetime.now(timezone.utc))
    used = await session.scalar(
        select(func.count())
        .select_from(ValidationResult)
        .where(
            ValidationResult.node_id.in_(node_ids),
            ValidationResult.created_at >= start,
        )
    )
    if (used or 0) >= limit:
        raise QuotaExceeded(f"monthly quota {limit} reached for tier {tier}")
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && pytest tests/integration/test_quota.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/coherence/models.py backend/app/entitlements/quota.py backend/tests/integration/test_quota.py
git commit -m "feat(coherence): ValidationResult model + monthly quota enforcement"
```

---

## Task 17: Coherence — the 5-step pipeline (integration, TDD, fake gateway)

**Files:**
- Create: `backend/app/coherence/pipeline.py`, `backend/app/coherence/schemas.py`, `backend/tests/integration/test_pipeline.py`

This is the heart. The pipeline: **(1) dedup by hash → (2) pre-checks → (3) quota+budget+LLM → (4) structured output → (5) persist + gate**, fail-closed throughout.

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_pipeline.py`

```python
from datetime import date

import pytest
from sqlalchemy import func, select

from app.coherence.contracts import CoherenceVerdict
from app.coherence.models import ValidationResult
from app.coherence.pipeline import PipelineOutcome, validate_node
from app.constructor import service as cservice
from app.constructor.node_types import NodeType
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import LLMTimeout


class FakeGateway:
    def __init__(self, *, score=85, raises=None):
        self.calls = 0
        self._score = score
        self._raises = raises

    def validate(self, *, model, system_prompt, user_prompt, today):
        self.calls += 1
        if self._raises:
            raise self._raises
        return LLMResult(
            verdict=CoherenceVerdict(score=self._score, issues=[], suggestions=[], summary="s"),
            model_used=model, tokens_used=42, cost_usd=0.002,
        )


async def _project_with_problema(db_session, content):
    p = await cservice.create_project(db_session, "u", "T", "es")
    await cservice.upsert_node_content(db_session, "u", p.id, NodeType.problema, content)
    return p


@pytest.mark.asyncio
async def test_happy_path_persists_and_marks_valido(db_session):
    gw = FakeGateway(score=90)
    p = await _project_with_problema(db_session, " ".join(["palabra"] * 40))

    out = await validate_node(
        db_session, gateway=gw, user_id="u", tier="free",
        project_id=p.id, node_type=NodeType.problema, today=date(2026, 6, 7),
    )
    assert out.status == PipelineOutcome.validated
    assert out.verdict.score == 90
    assert out.gate.blocked is False
    assert gw.calls == 1

    # node now 🟢
    _, nodes = await cservice.get_graph(db_session, "u", p.id)
    problema_state = next(s for n, s in nodes if n.type == "problema")
    assert problema_state == "valido"


@pytest.mark.asyncio
async def test_dedup_returns_cached_without_calling_llm(db_session):
    gw = FakeGateway(score=90)
    p = await _project_with_problema(db_session, " ".join(["palabra"] * 40))
    args = dict(user_id="u", tier="free", project_id=p.id,
               node_type=NodeType.problema, today=date(2026, 6, 7))

    await validate_node(db_session, gateway=gw, **args)
    out2 = await validate_node(db_session, gateway=gw, **args)
    assert out2.status == PipelineOutcome.cached
    assert gw.calls == 1  # second call did NOT hit the gateway


@pytest.mark.asyncio
async def test_precheck_too_short_skips_llm(db_session):
    gw = FakeGateway()
    p = await _project_with_problema(db_session, "muy corto")
    out = await validate_node(
        db_session, gateway=gw, user_id="u", tier="free",
        project_id=p.id, node_type=NodeType.problema, today=date(2026, 6, 7),
    )
    assert out.status == PipelineOutcome.precheck_failed
    assert gw.calls == 0


@pytest.mark.asyncio
async def test_llm_failure_is_fail_closed_node_not_valido(db_session):
    gw = FakeGateway(raises=LLMTimeout("slow"))
    p = await _project_with_problema(db_session, " ".join(["palabra"] * 40))
    out = await validate_node(
        db_session, gateway=gw, user_id="u", tier="free",
        project_id=p.id, node_type=NodeType.problema, today=date(2026, 6, 7),
    )
    assert out.status == PipelineOutcome.llm_failed
    # no ValidationResult persisted, node stays obsoleto/sin_validar (NOT valido)
    count = await db_session.scalar(select(func.count()).select_from(ValidationResult))
    assert count == 0
    _, nodes = await cservice.get_graph(db_session, "u", p.id)
    assert next(s for n, s in nodes if n.type == "problema") != "valido"


@pytest.mark.asyncio
async def test_doctoral_strict_blocks_low_score(db_session):
    gw = FakeGateway(score=40)
    p = await _project_with_problema(db_session, " ".join(["palabra"] * 40))
    out = await validate_node(
        db_session, gateway=gw, user_id="u", tier="doctoral",
        project_id=p.id, node_type=NodeType.problema, today=date(2026, 6, 7),
    )
    assert out.status == PipelineOutcome.validated  # it DID validate
    assert out.gate.mode == "estricto"
    assert out.gate.blocked is True               # but gate blocks progression
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/integration/test_pipeline.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement schemas** — `backend/app/coherence/schemas.py`

```python
from pydantic import BaseModel

from app.coherence.contracts import Issue


class ValidationOut(BaseModel):
    status: str                 # PipelineOutcome value
    score: int | None = None
    issues: list[Issue] = []
    suggestions: list[str] = []
    summary: str | None = None
    mode: str | None = None     # asesor | estricto
    blocked: bool = False
    message: str | None = None  # for precheck/llm-failure user messaging
    node_state: str | None = None
```

- [ ] **Step 4: Implement the pipeline** — `backend/app/coherence/pipeline.py`

```python
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coherence.contracts import CoherenceVerdict
from app.coherence.models import ValidationResult
from app.coherence.prechecks import run_prechecks
from app.constructor.freshness import Freshness, compute_state
from app.constructor.hashing import compute_node_hash
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import NodeType, upstream_types
from app.entitlements.errors import QuotaExceeded
from app.entitlements.gate import GateResult, apply_gate
from app.entitlements.quota import consume_monthly_quota
from app.entitlements.tiers import Tier, TIER_CONFIG
from app.i18n.prompts import SYSTEM_PROMPT_ES, build_user_prompt
from app.llm_gateway.errors import LLMError


class PipelineOutcome(StrEnum):
    cached = "cached"
    precheck_failed = "precheck_failed"
    quota_exceeded = "quota_exceeded"
    llm_failed = "llm_failed"
    validated = "validated"


@dataclass
class PipelineResult:
    status: PipelineOutcome
    verdict: CoherenceVerdict | None = None
    gate: GateResult | None = None
    message: str | None = None
    node_state: str | None = None


async def _load(session: AsyncSession, user_id: str, project_id: str):
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise LookupError("project not found")
    res = await session.scalars(select(Node).where(Node.project_id == project_id))
    nodes = {NodeType(n.type): n for n in res}
    return project, nodes


async def _user_node_ids(session: AsyncSession, user_id: str) -> list[str]:
    rows = await session.scalars(
        select(Node.id)
        .join(ResearchProject, ResearchProject.id == Node.project_id)
        .where(ResearchProject.user_id == user_id)
    )
    return list(rows)


async def validate_node(
    session: AsyncSession,
    *,
    gateway,
    user_id: str,
    tier: str,
    project_id: str,
    node_type: NodeType,
    today: date,
) -> PipelineResult:
    _, nodes = await _load(session, user_id, project_id)
    node = nodes[node_type]
    contents = {nt: n.content for nt, n in nodes.items()}
    current_hash = compute_node_hash(node_type, contents)
    state = compute_state(current_hash, node.last_validated_hash)

    # STEP 1 — dedup by hash (zero cost)
    if state == Freshness.valido:
        last = await session.scalar(
            select(ValidationResult)
            .where(ValidationResult.node_id == node.id)
            .order_by(ValidationResult.created_at.desc())
        )
        if last is not None:
            verdict = _verdict_from_row(last)
            return PipelineResult(
                PipelineOutcome.cached, verdict=verdict,
                gate=apply_gate(verdict, Tier(tier)), node_state=state.value,
            )

    # STEP 2 — deterministic pre-checks (no LLM)
    upstream_states = {
        dep: compute_state(compute_node_hash(dep, contents), nodes[dep].last_validated_hash)
        for dep in upstream_types(node_type)
    }
    pre = run_prechecks(node_type, node.content, upstream_states)
    if not pre.ok:
        return PipelineResult(
            PipelineOutcome.precheck_failed, message=pre.message, node_state=state.value
        )

    # STEP 3 — guardrails + the single paid call
    try:
        await consume_monthly_quota(
            session, user_id, await _user_node_ids(session, user_id), tier
        )
    except QuotaExceeded as e:
        return PipelineResult(
            PipelineOutcome.quota_exceeded, message=str(e), node_state=state.value
        )

    cfg = TIER_CONFIG[Tier(tier)]
    from app.config import get_settings

    model = cfg.anthropic_model if get_settings().llm_provider == "anthropic" else cfg.openai_model
    upstream_content = {dep: nodes[dep].content for dep in upstream_types(node_type)}
    try:
        result = gateway.validate(
            model=model,
            system_prompt=SYSTEM_PROMPT_ES,
            user_prompt=build_user_prompt(node_type, node.content, upstream_content),
            today=today,
        )
    except LLMError as e:
        # STEP 5 (fail-closed): persist nothing, node stays NOT valido
        return PipelineResult(
            PipelineOutcome.llm_failed,
            message="No pudimos validar con confianza, reintenta.",
            node_state=state.value,
        )

    # STEP 4 + 5 — persist + update hash + gate (single transaction)
    verdict = result.verdict
    session.add(
        ValidationResult(
            node_id=node.id,
            score=verdict.score,
            issues=[i.model_dump() for i in verdict.issues],
            suggestions=verdict.suggestions,
            model_used=result.model_used,
            tokens_used=result.tokens_used,
            cost_usd=result.cost_usd,
        )
    )
    node.last_validated_hash = current_hash
    await session.commit()

    return PipelineResult(
        PipelineOutcome.validated,
        verdict=verdict,
        gate=apply_gate(verdict, Tier(tier)),
        node_state=Freshness.valido.value,
    )


def _verdict_from_row(row: ValidationResult) -> CoherenceVerdict:
    return CoherenceVerdict(
        score=row.score,
        issues=row.issues,
        suggestions=row.suggestions,
        summary="",
    )
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && pytest tests/integration/test_pipeline.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/coherence/pipeline.py backend/app/coherence/schemas.py backend/tests/integration/test_pipeline.py
git commit -m "feat(coherence): 5-step validation pipeline (dedup/precheck/llm/persist/gate)"
```

---

## Task 18: Coherence — HTTP endpoint + gateway wiring (integration, TDD)

**Files:**
- Create: `backend/app/coherence/service.py`, `backend/app/coherence/router.py`, `backend/tests/integration/test_coherence_api.py`
- Modify: `backend/app/main.py`

The router needs a real `LLMGateway`, but tests must inject a fake. We provide a FastAPI dependency `get_gateway` that is overridden in tests.

- [ ] **Step 1: Write the failing test** — `backend/tests/integration/test_coherence_api.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/integration/test_coherence_api.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement service (gateway factory)** — `backend/app/coherence/service.py`

```python
from functools import lru_cache

from app.config import get_settings
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.gateway import LLMGateway
from app.llm_gateway.providers.anthropic_provider import AnthropicProvider
from app.llm_gateway.providers.openai_provider import OpenAIProvider


@lru_cache
def _singleton_gateway() -> LLMGateway:
    s = get_settings()
    if s.llm_provider == "openai":
        provider = OpenAIProvider(api_key=s.openai_api_key)
    else:
        provider = AnthropicProvider(api_key=s.anthropic_api_key)
    return LLMGateway(
        provider=provider,
        budget=DailyBudget(limit_usd=s.daily_budget_usd),
        breaker=CircuitBreaker(s.circuit_breaker_threshold, s.circuit_breaker_cooldown_s),
        timeout_s=s.llm_timeout_s,
    )


def get_gateway() -> LLMGateway:
    """FastAPI dependency; overridden in tests with a fake."""
    return _singleton_gateway()
```

- [ ] **Step 4: Implement router** — `backend/app/coherence/router.py`

```python
from datetime import date, timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.coherence import pipeline
from app.coherence.schemas import ValidationOut
from app.coherence.service import get_gateway
from app.constructor.node_types import NodeType
from app.db import get_session

router = APIRouter(prefix="/api/projects", tags=["coherence"])


@router.post("/{project_id}/nodes/{node_type}/validate", response_model=ValidationOut)
async def validate(
    project_id: str,
    node_type: NodeType,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    gateway=Depends(get_gateway),
):
    try:
        out = await pipeline.validate_node(
            session,
            gateway=gateway,
            user_id=user.id,
            tier=user.tier,
            project_id=project_id,
            node_type=node_type,
            today=datetime.now(timezone.utc).date(),
        )
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

    return ValidationOut(
        status=out.status.value,
        score=out.verdict.score if out.verdict else None,
        issues=out.verdict.issues if out.verdict else [],
        suggestions=out.verdict.suggestions if out.verdict else [],
        summary=out.verdict.summary if out.verdict else None,
        mode=out.gate.mode if out.gate else None,
        blocked=out.gate.blocked if out.gate else False,
        message=out.message,
        node_state=out.node_state,
    )
```

- [ ] **Step 5: Wire router** — add to `backend/app/main.py`

```python
from app.coherence.router import router as coherence_router
# ...
app.include_router(coherence_router)
```

- [ ] **Step 6: Run to verify it passes + full suite**

Run: `cd backend && pytest tests/integration/test_coherence_api.py -v && pytest -q`
Expected: the targeted test passes; full suite green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/coherence/service.py backend/app/coherence/router.py backend/tests/integration/test_coherence_api.py backend/app/main.py
git commit -m "feat(coherence): validate endpoint with injectable gateway"
```

---

## Task 19: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Initialize alembic config** — `backend/alembic.ini` (minimal, key lines)

```ini
[alembic]
script_location = alembic
sqlalchemy.url =

[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Implement `backend/alembic/env.py`** (async, reads `DATABASE_URL`, autogenerate target)

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.config import get_settings
from app.db import Base
import app.auth.models      # noqa: F401
import app.constructor.models  # noqa: F401
import app.coherence.models    # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

- [ ] **Step 3: Generate the initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```
Expected: a file in `alembic/versions/` creating `users`, `research_projects`, `nodes`, `validation_results`. Rename it to `0001_initial.py` for clarity.

- [ ] **Step 4: Apply against a scratch DB to verify**

```bash
cd backend && DATABASE_URL="postgresql+asyncpg://velvyko:velvyko@localhost:5432/velvyko" alembic upgrade head
```
Expected: `Running upgrade -> 0001, initial schema`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/env.py backend/alembic/versions
git commit -m "feat(db): alembic async migrations + initial schema"
```

---

## Task 20: LLM evals harness (NOT in CI)

**Files:**
- Create: `backend/tests/evals/__init__.py`, `backend/tests/evals/golden_dataset.py`, `backend/tests/evals/run_evals.py`

These call the **real** LLM. They are never run in CI (cost + non-determinism). Run manually or via the existing **n8n** (verified running on the VPS, reachable through the n8n MCP) on rubric/prompt changes.

- [ ] **Step 1: Create the golden dataset** — `backend/tests/evals/golden_dataset.py` (seed with ~6 cases; grow to 20–50)

```python
from dataclasses import dataclass

from app.constructor.node_types import NodeType


@dataclass(frozen=True)
class EvalCase:
    name: str
    node_type: NodeType
    content: str
    upstream: dict[NodeType, str]
    expected_score_min: int
    expected_score_max: int
    expected_dimension: str | None  # a dimension that SHOULD appear in issues, or None


CASES: list[EvalCase] = [
    EvalCase(
        name="problema_solido",
        node_type=NodeType.problema,
        content=(
            "Existe un vacío sobre cómo la carga cognitiva afecta la retención en "
            "estudiantes de posgrado en entornos de aprendizaje en línea sincrónico, "
            "lo que limita el diseño de intervenciones efectivas."
        ),
        upstream={},
        expected_score_min=70, expected_score_max=100, expected_dimension=None,
    ),
    EvalCase(
        name="hipotesis_no_falsable",
        node_type=NodeType.hipotesis,
        content="La educación es importante para el éxito de las personas.",
        upstream={NodeType.problema: "Vacío sobre carga cognitiva y retención.",
                  NodeType.objetivos: "Medir el efecto de la carga cognitiva."},
        expected_score_min=0, expected_score_max=50, expected_dimension="falsabilidad",
    ),
    # ... add more cases (objetivos desalineados, variables no medibles, etc.)
]
```

- [ ] **Step 2: Create the runner** — `backend/tests/evals/run_evals.py`

```python
"""Run with: python -m tests.evals.run_evals  (requires real API keys; costs money)."""
from datetime import date

from app.coherence.service import _singleton_gateway
from app.i18n.prompts import SYSTEM_PROMPT_ES, build_user_prompt
from tests.evals.golden_dataset import CASES


def main() -> None:
    gw = _singleton_gateway()
    passed = 0
    for c in CASES:
        res = gw.validate(
            model="claude-haiku-4-5-20251001",
            system_prompt=SYSTEM_PROMPT_ES,
            user_prompt=build_user_prompt(c.node_type, c.content, c.upstream),
            today=date.today(),
        )
        v = res.verdict
        score_ok = c.expected_score_min <= v.score <= c.expected_score_max
        dim_ok = c.expected_dimension is None or any(
            i.dimension == c.expected_dimension for i in v.issues
        )
        ok = score_ok and dim_ok
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {c.name}: score={v.score} dims={[i.dimension for i in v.issues]}")
    print(f"\n{passed}/{len(CASES)} eval cases passed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Sanity-check it imports (do NOT run without keys)**

Run: `cd backend && python -c "import tests.evals.run_evals; print('import ok')"`
Expected: `import ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/evals
git commit -m "test(evals): golden dataset + runner (excluded from CI)"
```

- [ ] **Step 5: (Optional) Schedule via existing n8n — built through the n8n MCP**

The VPS already runs n8n (`n8n-dlyc`, reachable via the n8n MCP). To run evals on a cadence without standing up new infra, create a workflow `velvyko-evals` (in the personal project) with:
- **Schedule Trigger** (e.g. weekly, or manual) →
- **HTTP Request** to a small backend eval endpoint (or n8n **Execute Command** invoking `python -m tests.evals.run_evals` inside the `velvyko-backend` container) →
- notify on regressions (e.g. Telegram/email node) if `passed < len(CASES)`.

Build it with the SDK flow the n8n MCP exposes: `get_sdk_reference` → `search_nodes(["schedule trigger","http request"])` → `get_node_types` → `validate_workflow` → `create_workflow_from_code`. n8n reaches the backend over the shared `clinic-net` network (`http://velvyko-backend:8000`). Keep it namespaced `velvyko-evals` so it's clearly separate from the production clinic workflows.

---

## Task 21: Frontend scaffold + API client + auth

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/auth/AuthContext.tsx`, `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Scaffold Vite + React + TS**

```bash
cd frontend && npm create vite@latest . -- --template react-ts && npm install && npm install @tanstack/react-query react-router-dom
```
Expected: project files created; deps installed.

- [ ] **Step 2: Create `frontend/src/api/types.ts`**

```typescript
export type Tier = "free" | "pro" | "doctoral" | "university";
export type NodeState = "sin_validar" | "valido" | "obsoleto";
export type NodeType =
  | "problema" | "objetivos" | "hipotesis"
  | "variables" | "metodologia" | "instrumentos";

export interface NodeOut { type: NodeType; content: string; state: NodeState; }
export interface ProjectDetail { id: string; title: string; language: string; nodes: NodeOut[]; }
export interface ProjectSummary { id: string; title: string; language: string; }
export interface Issue {
  severity: "critica" | "mayor" | "menor";
  dimension: string; explanation: string; location: string | null;
}
export interface ValidationOut {
  status: string; score: number | null; issues: Issue[];
  suggestions: string[]; summary: string | null;
  mode: string | null; blocked: boolean; message: string | null;
  node_state: NodeState | null;
}
```

- [ ] **Step 3: Create `frontend/src/api/client.ts`**

```typescript
const BASE = "/api";

function token(): string | null { return localStorage.getItem("velvyko_token"); }

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as any) };
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    req("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    req<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req<{ id: string; email: string; tier: string }>("/auth/me"),
  projects: () => req("/projects"),
  createProject: (title: string) =>
    req("/projects", { method: "POST", body: JSON.stringify({ title }) }),
  project: (id: string) => req(`/projects/${id}`),
  saveNode: (pid: string, type: string, content: string) =>
    req(`/projects/${pid}/nodes/${type}`, { method: "PUT", body: JSON.stringify({ content }) }),
  validate: (pid: string, type: string) =>
    req(`/projects/${pid}/nodes/${type}/validate`, { method: "POST" }),
};
```

- [ ] **Step 4: Create `frontend/src/auth/AuthContext.tsx`**

```typescript
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "../api/client";

interface AuthState { email: string | null; login: (e: string, p: string) => Promise<void>;
  register: (e: string, p: string) => Promise<void>; logout: () => void; }

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    if (localStorage.getItem("velvyko_token")) api.me().then((u: any) => setEmail(u.email)).catch(() => {});
  }, []);
  const login = async (e: string, p: string) => {
    const r = await api.login(e, p);
    localStorage.setItem("velvyko_token", r.access_token);
    const u: any = await api.me(); setEmail(u.email);
  };
  const register = async (e: string, p: string) => { await api.register(e, p); await login(e, p); };
  const logout = () => { localStorage.removeItem("velvyko_token"); setEmail(null); };
  return <Ctx.Provider value={{ email, login, register, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside provider");
  return c;
};
```

- [ ] **Step 5: Create `frontend/src/pages/LoginPage.tsx`**

```typescript
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login, register } = useAuth();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { mode === "login" ? await login(email, pw) : await register(email, pw); }
    catch (x: any) { setErr(x.message); }
  };
  return (
    <form onSubmit={submit} style={{ maxWidth: 320, margin: "4rem auto", display: "grid", gap: 8 }}>
      <h1>Velvyko</h1>
      <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="contraseña" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      <button type="submit">{mode === "login" ? "Entrar" : "Crear cuenta"}</button>
      <a onClick={() => setMode(mode === "login" ? "register" : "login")} style={{ cursor: "pointer" }}>
        {mode === "login" ? "Crear una cuenta" : "Ya tengo cuenta"}
      </a>
    </form>
  );
}
```

- [ ] **Step 6: Create `frontend/src/main.tsx`** (router + providers; full app routes added in Task 22-23)

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LoginPage } from "./pages/LoginPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProjectPage } from "./pages/ProjectPage";

const qc = new QueryClient();

function Guard({ children }: { children: JSX.Element }) {
  return localStorage.getItem("velvyko_token") ? children : <Navigate to="/login" />;
}

function App() {
  const { email } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={email ? <Navigate to="/" /> : <LoginPage />} />
      <Route path="/" element={<Guard><ProjectsPage /></Guard>} />
      <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider><App /></AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
```

- [ ] **Step 7: Configure dev proxy** — `frontend/vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
```

- [ ] **Step 8: Verify build (ProjectsPage/ProjectPage come next; create stubs to compile)**

Create temporary stubs so it compiles:
```bash
cd frontend
printf 'export function ProjectsPage(){return <div/>;}' > src/pages/ProjectsPage.tsx
printf 'export function ProjectPage(){return <div/>;}' > src/pages/ProjectPage.tsx
npm run build
```
Expected: build succeeds. (Real implementations replace the stubs in Tasks 22–23.)

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src
git commit -m "feat(frontend): vite scaffold, api client, auth, login page"
```

---

## Task 22: Frontend — projects list & create

**Files:**
- Replace: `frontend/src/pages/ProjectsPage.tsx`

- [ ] **Step 1: Implement `ProjectsPage.tsx`**

```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { ProjectSummary } from "../api/types";

export function ProjectsPage() {
  const nav = useNavigate(); const qc = useQueryClient(); const { email, logout } = useAuth();
  const [title, setTitle] = useState("");
  const { data: projects = [] } = useQuery<ProjectSummary[]>({
    queryKey: ["projects"], queryFn: () => api.projects() as any,
  });
  const create = useMutation({
    mutationFn: () => api.createProject(title) as any,
    onSuccess: (p: any) => { qc.invalidateQueries({ queryKey: ["projects"] }); nav(`/projects/${p.id}`); },
  });
  return (
    <div style={{ maxWidth: 700, margin: "2rem auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Mis investigaciones</h1>
        <span>{email} · <a onClick={logout} style={{ cursor: "pointer" }}>salir</a></span>
      </header>
      <div style={{ display: "flex", gap: 8, margin: "1rem 0" }}>
        <input placeholder="Título de la investigación" value={title}
               onChange={(e) => setTitle(e.target.value)} style={{ flex: 1 }} />
        <button disabled={!title.trim()} onClick={() => create.mutate()}>Crear</button>
      </div>
      <ul>
        {projects.map((p) => (
          <li key={p.id}><a onClick={() => nav(`/projects/${p.id}`)} style={{ cursor: "pointer" }}>{p.title}</a></li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProjectsPage.tsx
git commit -m "feat(frontend): projects list and create"
```

---

## Task 23: Frontend — constructor (node editor, freshness badges, validation panel)

**Files:**
- Create: `frontend/src/components/FreshnessBadge.tsx`, `frontend/src/components/NodeEditor.tsx`, `frontend/src/components/ValidationPanel.tsx`
- Replace: `frontend/src/pages/ProjectPage.tsx`

- [ ] **Step 1: Implement `FreshnessBadge.tsx`**

```typescript
import type { NodeState } from "../api/types";

const MAP: Record<NodeState, { icon: string; label: string }> = {
  sin_validar: { icon: "⚪", label: "Sin validar" },
  valido: { icon: "🟢", label: "Válido" },
  obsoleto: { icon: "🟡", label: "Obsoleto" },
};

export function FreshnessBadge({ state }: { state: NodeState }) {
  const m = MAP[state];
  return <span title={m.label}>{m.icon} {m.label}</span>;
}
```

- [ ] **Step 2: Implement `ValidationPanel.tsx`**

```typescript
import type { ValidationOut } from "../api/types";

export function ValidationPanel({ result }: { result: ValidationOut | null }) {
  if (!result) return null;
  if (result.status !== "validated" && result.status !== "cached") {
    return <div style={{ background: "#fff7e6", padding: 12, borderRadius: 8 }}>
      ⚠️ {result.message ?? "No se pudo validar."}
    </div>;
  }
  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
      <strong>Puntaje: {result.score}/100</strong>
      {result.mode === "estricto" && result.blocked &&
        <p style={{ color: "crimson" }}>🔒 Modo estricto: no puedes avanzar hasta mejorar este nodo.</p>}
      {result.summary && <p>{result.summary}</p>}
      {result.issues.length > 0 && (
        <ul>{result.issues.map((i, k) => (
          <li key={k}><b>[{i.severity}/{i.dimension}]</b> {i.explanation}</li>
        ))}</ul>
      )}
      {result.suggestions.length > 0 && (
        <><h4>Sugerencias</h4>
        <ul>{result.suggestions.map((s, k) => <li key={k}>{s}</li>)}</ul></>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Implement `NodeEditor.tsx`**

```typescript
import { useState } from "react";
import type { NodeOut, ValidationOut } from "../api/types";
import { FreshnessBadge } from "./FreshnessBadge";
import { ValidationPanel } from "./ValidationPanel";

interface Props {
  node: NodeOut;
  onSave: (content: string) => Promise<void>;
  onValidate: () => Promise<ValidationOut>;
}

export function NodeEditor({ node, onSave, onValidate }: Props) {
  const [content, setContent] = useState(node.content);
  const [result, setResult] = useState<ValidationOut | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section style={{ marginBottom: 24 }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h3 style={{ textTransform: "capitalize" }}>{node.type}</h3>
        <FreshnessBadge state={node.state} />
      </header>
      <textarea rows={5} style={{ width: "100%" }} value={content}
                onChange={(e) => setContent(e.target.value)} onBlur={() => onSave(content)} />
      <button disabled={busy} onClick={async () => {
        setBusy(true); await onSave(content);
        try { setResult(await onValidate()); } finally { setBusy(false); }
      }}>{busy ? "Validando…" : "Validar coherencia"}</button>
      <ValidationPanel result={result} />
    </section>
  );
}
```

- [ ] **Step 4: Implement `ProjectPage.tsx`**

```typescript
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ProjectDetail, ValidationOut } from "../api/types";
import { NodeEditor } from "../components/NodeEditor";

export function ProjectPage() {
  const { id = "" } = useParams(); const qc = useQueryClient();
  const { data } = useQuery<ProjectDetail>({
    queryKey: ["project", id], queryFn: () => api.project(id) as any,
  });
  if (!data) return <p style={{ margin: "2rem" }}>Cargando…</p>;
  return (
    <div style={{ maxWidth: 760, margin: "2rem auto" }}>
      <h1>{data.title}</h1>
      {data.nodes.map((n) => (
        <NodeEditor key={n.type} node={n}
          onSave={async (c) => { await api.saveNode(id, n.type, c); qc.invalidateQueries({ queryKey: ["project", id] }); }}
          onValidate={async () => {
            const r = await api.validate(id, n.type) as ValidationOut;
            qc.invalidateQueries({ queryKey: ["project", id] });
            return r;
          }} />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components frontend/src/pages/ProjectPage.tsx
git commit -m "feat(frontend): constructor with node editor, freshness, validation panel"
```

---

## Task 24: Deployment — Dockerfiles, docker-compose (Traefik + dedicated Postgres), README

**Files:**
- Create: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `Caddyfile` (local dev only), `README.md`

> Production uses the **existing Traefik** (host-mode, Docker provider, Let's Encrypt) via labels and a **dedicated `velvyko-postgres`** (`pgvector/pgvector:pg16`) on the external `clinic-net` network. No Caddy in prod. The SPA is served by a tiny `nginx:alpine` container (also label-routed by Traefik). The `Caddyfile` (Task 23 / Step 7 here) is **local-dev only**.

- [ ] **Step 1: Backend Dockerfile** — `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- [ ] **Step 2: Frontend Dockerfile (build + nginx static serve)** — `frontend/Dockerfile`

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`frontend/nginx.conf` (SPA fallback; `/api` is routed to the backend by Traefik, not here):
```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

- [ ] **Step 3: `docker-compose.yml`** — dedicated Postgres + Traefik labels on `clinic-net`

The Velvyko backend and frontend carry Traefik labels. Traefik (host-mode, reading the Docker socket) discovers them on `clinic-net` and terminates TLS. `velvyko.${VELVYKO_HOST}` → frontend; the same host with `PathPrefix(/api)` → backend (higher priority). `velvyko-postgres` stays internal (no labels, no published ports).

```yaml
services:
  velvyko-postgres:
    image: pgvector/pgvector:pg16
    container_name: velvyko-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    command: postgres -c max_connections=50
    volumes:
      - velvyko_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks: [clinic-net]

  backend:
    build: ./backend
    container_name: velvyko-backend
    env_file: .env
    depends_on:
      velvyko-postgres:
        condition: service_healthy
    expose: ["8000"]
    restart: unless-stopped
    networks: [clinic-net]
    labels:
      - traefik.enable=true
      - traefik.docker.network=clinic-net
      - traefik.http.routers.velvyko-api.rule=Host(`${VELVYKO_HOST}`) && PathPrefix(`/api`)
      - traefik.http.routers.velvyko-api.priority=20
      - traefik.http.routers.velvyko-api.entrypoints=websecure
      - traefik.http.routers.velvyko-api.tls.certresolver=letsencrypt
      - traefik.http.services.velvyko-api.loadbalancer.server.port=8000

  frontend:
    build: ./frontend
    container_name: velvyko-frontend
    depends_on: [backend]
    restart: unless-stopped
    networks: [clinic-net]
    labels:
      - traefik.enable=true
      - traefik.docker.network=clinic-net
      - traefik.http.routers.velvyko-web.rule=Host(`${VELVYKO_HOST}`)
      - traefik.http.routers.velvyko-web.priority=10
      - traefik.http.routers.velvyko-web.entrypoints=websecure
      - traefik.http.routers.velvyko-web.tls.certresolver=letsencrypt
      - traefik.http.services.velvyko-web.loadbalancer.server.port=80

volumes:
  velvyko_pgdata:

networks:
  clinic-net:
    external: true       # the existing shared bridge; VERIFIED name = clinic-net
    name: clinic-net
```

> Notes: `DATABASE_URL` in `.env` points at `velvyko-postgres:5432` (service name on `clinic-net`). Traefik needs `traefik.docker.network=clinic-net` because containers may sit on more than one network. No `ports:` are published — Traefik reaches container bridge IPs directly.

- [ ] **Step 4: First-boot DB migration**

The dedicated Postgres starts empty. After `docker compose up -d --build`, run Alembic against it (the image already has pgvector available; the MVP creates no vector columns):
```bash
docker compose exec backend alembic upgrade head
```
Expected: migrations apply cleanly on the fresh `velvyko` DB.

- [ ] **Step 5: `README.md`** (run instructions)

```markdown
# Velvyko — Constructor + Coherence Engine (MVP)

## Local dev
1. Backend: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
2. Frontend: `cd frontend && npm install && npm run dev` (proxies /api to :8000)
3. DB: run `pgvector/pgvector:pg16` locally (or any Postgres 16), point `DATABASE_URL` at
   `localhost:5432`, then `cd backend && alembic upgrade head`.
   Optionally use the local-dev `Caddyfile` to serve SPA + proxy /api on one origin.

## Tests
- All deterministic tests (CI): `cd backend && pytest`
- Evals (real LLM, costs money, NOT in CI): `cd backend && python -m tests.evals.run_evals`
  (or trigger the `velvyko-evals` n8n workflow on rubric/prompt changes — see Task 20)

## Deploy (shared 8 GB VPS srv1533829, via existing Traefik)
1. Fill `.env` from `.env.example` (DB creds, `VELVYKO_HOST`, JWT secret, LLM keys).
2. `docker compose up -d --build` (joins the external `clinic-net`; Traefik auto-issues TLS).
3. `docker compose exec backend alembic upgrade head`.
4. Visit `https://velvyko.srv1533829.hstgr.cloud`. Traefik routes `/api` → backend, rest → SPA.
   No Caddy, no published ports — routing is entirely via Traefik labels.
```

- [ ] **Step 6: Validate compose config**

Run: `docker compose config`
Expected: rendered config with no errors; `clinic-net` shown as external.

- [ ] **Step 7: `Caddyfile` (local dev only)** — single-origin SPA + /api proxy for `npm run dev` parity

```
{$SITE_ADDRESS:localhost} {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        root * /srv/www
        try_files {path} /index.html
        file_server
    }
}
```
> Not used in production (Traefik handles prod). Keep only if you want a one-origin local setup.

- [ ] **Step 8: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml Caddyfile README.md
git commit -m "feat(infra): dockerfiles, compose (traefik labels + dedicated pgvector pg), run docs"
```

---

## Task 25: CI test gate (exclude evals)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Implement workflow** — `.github/workflows/ci.yml`

```yaml
name: ci
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: cd backend && pip install -e ".[dev]"
      - run: cd backend && pytest tests/unit tests/integration -q   # evals excluded
  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm run build
```

- [ ] **Step 2: Verify the exact test path works locally**

Run: `cd backend && pytest tests/unit tests/integration -q`
Expected: all green; `tests/evals` not collected.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run deterministic tests + frontend build, exclude LLM evals"
```

---

## Self-Review (performed against the spec)

**Spec coverage:**
- §4 architecture/modules → Tasks 1, 7, 17, 18, 24 (module layout, monolith, Traefik labels/compose on shared VPS, RAM via static SPA + 2 workers).
- §5 data model + cascade → Tasks 4–7, 16 (User/Project/Node/ValidationResult, dependency chain, hash, freshness).
- §6 5-step pipeline + Pydantic contract + model-by-tier + 4 savings → Tasks 8, 9, 13, 14, 15, 17 (dedup, prechecks, prompt-cache via `cache_control`, tier model selection).
- §7 errors fail-closed + guardrails → Tasks 11, 12, 15, 16, 17 (budget kill switch, breaker, retry, quota, fail-closed pipeline path, transaction for result+hash).
- §8 test pyramid → unit tasks throughout, integration Tasks 3/7/16/17/18, evals Task 20, CI excludes evals Task 25.
- §9 phases 0–1 → all tasks (phase 2/3 features explicitly out of scope, per spec §3).
- §11 open questions → resolved in the Config Defaults table + the "Infrastructure — VERIFIED" table + Task 0 (Postgres/pgvector/proxy confirmed live on the VPS, not assumed).

**Placeholder scan:** No `TBD`/`implement later`. The eval dataset (Task 20) intentionally ships a seed of real cases with a comment to grow it — that is data volume, not a logic placeholder. Frontend stubs in Task 21 Step 8 are explicitly temporary and replaced in Tasks 22–23.

**Type consistency:** `CoherenceVerdict`/`Issue` fields (score, issues, suggestions, summary; severity/dimension/explanation/location) consistent across contracts (T8), gateway (T14/15), pipeline (T17), API schema (T18), frontend types (T21). `Freshness` values (`sin_validar`/`valido`/`obsoleto`) consistent across T6, prechecks T9, pipeline T17, frontend badge T23. `NodeType` values consistent backend (T4) ↔ frontend (T21). `PipelineOutcome` values used identically in T17 logic and T17/T18 tests. `validate_node(...)` signature matches its callers in T17 tests and T18 router.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-07-velvyko-constructor-coherence.md`.**
