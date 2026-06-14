# Velvyko — Constructor + Coherence Engine (MVP)

Inteligencia Metodológica Científica: un **Constructor** de investigación con 6 nodos
metodológicos (problema → objetivos → hipótesis → variables → metodología →
instrumentos) y un **Scientific Coherence Engine** (LLM-juez con salida estructurada,
frescura en cascada por hash, gate asesor/estricto por tier, guardrails de costo,
errores fail-closed).

**Verificación de citas (Fase 2):** módulo `verification` + panel "Verificación de citas"
que, bajo demanda, valida el formato APA-7 de las citas en-texto (checks deterministas +
revisión de estilo LLM tier-gated) y verifica su existencia contra Crossref/OpenAlex
(anti-alucinación, fail-closed), limitado a 10 ejecuciones/min por proyecto.

## API

- `POST /api/projects/{project_id}/verify-citations` — ejecuta la verificación de citas
  (checks de formato APA-7 + lookup de existencia Crossref/OpenAlex + revisión de estilo
  LLM por tier), limitado por proyecto; devuelve un `CitationRunOut`.
- `GET /api/projects/{project_id}/verify-citations/latest` — último run de verificación
  persistido del proyecto (404 si no hay ninguno).

## Local dev
1. Backend: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
2. Frontend: `cd frontend && npm install && npm run dev` (proxies /api to :8000)
3. DB: run `pgvector/pgvector:pg16` locally (or any Postgres 16), point `DATABASE_URL` at
   `localhost:5432`, then `cd backend && alembic upgrade head`.
   Optionally use the local-dev `Caddyfile` to serve SPA + proxy /api on one origin.

## Tests
- All deterministic tests (CI): `cd backend && pytest`
- Evals (real LLM, costs money, NOT in CI): `cd backend && python -m tests.evals.run_evals`
  (or trigger the `velvyko-evals` n8n workflow on rubric/prompt changes)

## Deploy (shared 8 GB VPS srv1533829, via existing Traefik)
Infra verified live on the VPS: reverse proxy = **Traefik** (host-mode, Docker provider,
Let's Encrypt); shared Docker network = **`clinic-net`**; Velvyko runs a **dedicated
`velvyko-postgres`** (`pgvector/pgvector:pg16`) — NOT the clinic Postgres.

1. Fill `.env` from `.env.example` (DB creds, `VELVYKO_HOST`, JWT secret, LLM keys).
2. `docker compose up -d --build` (joins the external `clinic-net`; Traefik auto-issues TLS).
3. `docker compose exec backend alembic upgrade head`.
4. Visit `https://velvyko.srv1533829.hstgr.cloud`. Traefik routes `/api` → backend, rest → SPA.
   No Caddy, no published ports — routing is entirely via Traefik labels.
