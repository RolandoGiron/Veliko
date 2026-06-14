# Velvyko — Fase 2: Verificación de citas (APA + anti-alucinación) — Diseño

**Fecha:** 2026-06-11 · **Estado:** aprobado en brainstorming
**Antecedente:** roadmap §9 del spec del MVP (`2026-06-06-velvyko-constructor-coherence-design.md`): Fase 2 = "APA validation + DOI/anti-alucinación".

---

## 1. Qué construye

Un nuevo módulo backend `verification` + panel frontend "Verificación" que, bajo demanda
(`Verificar citas`), procesa los **6 nodos existentes** de un proyecto:

1. **Extrae** todas las citas APA en-texto del contenido de cada nodo (determinista, gratis).
2. **Valida el formato APA-7** de cada cita: capa determinista siempre; capa LLM-juez
   (matices de estilo) solo para tiers de pago, vía el `llm_gateway` existente.
3. **Verifica existencia** contra **Crossref** y **OpenAlex** (APIs públicas gratuitas, sin
   API key): ¿existe literatura publicada de ese autor en ese año? Si ninguna de las dos
   fuentes devuelve resultados → **⚠ posible cita inventada** (anti-alucinación).

Decisiones tomadas con el usuario (2026-06-11):
- **Alcance:** solo Fase 2. Attack Mode y billing (Fase 3) quedan para un spec aparte.
- **Dónde viven las referencias:** NO hay sección/nodo de bibliografía. Se verifican las
  **citas en-texto dentro de los 6 nodos** (`García (2020)`, `(García & López, 2019)`).
- **Validación APA:** híbrida — determinista + LLM.

## 2. No-objetivos (YAGNI)

- Lista de referencias / bibliografía por proyecto (posible Fase 2.5).
- Parseo de referencias completas APA (autor, título, revista…) — no existen en los nodos.
- Verificación de DOI literal pegado en el texto.
- Citas de normas distintas a APA-7 (Vancouver, MLA…).
- Cambios a la cadena de dependencias, hashing o freshness del constructor.

## 3. Gramática de citas reconocida (extracción determinista)

Variantes APA-7 en español que el extractor reconoce (regex, sin LLM):

| Forma | Ejemplos |
|---|---|
| Narrativa | `García (2020)` · `García y López (2019)` · `García et al. (2021)` |
| Parentética | `(García, 2020)` · `(García & López, 2019)` · `(García et al., 2021, p. 23)` |
| Múltiple | `(García, 2019; López, 2020)` → 2 citas |
| Año | `2020`, `2020a`, `s.f.` (sin fecha) |

Cada cita extraída produce: `Citation(node_type, raw_text, surname, year, narrative: bool)`.
Para citas multi-autor el `surname` es el primer apellido (es la clave de búsqueda).
Citas `s.f.` se extraen pero **no** se buscan externamente (sin año ⇒ búsqueda inútil);
su `existence_status` = `no_verificable` con mensaje explicativo.

## 4. Checks APA-7 deterministas (gratis, siempre activos)

Emiten issues `{severity: critica|mayor|menor, code, message_es, citation}`:

| Code | Regla | Severidad |
|---|---|---|
| `falta_coma` | Parentética sin coma antes del año: `(García 2020)` | mayor |
| `ampersand_en_narrativa` | `&` en cita narrativa (debe ser `y`) | menor |
| `y_en_parentetica` | `y` dentro de paréntesis (APA usa `&`) | menor |
| `demasiados_autores` | 3+ apellidos listados en vez de `et al.` | mayor |
| `anio_futuro` | Año > año actual + 1 | mayor |
| `sin_citas` | Proyecto sin ninguna cita en ningún nodo | menor (informativo) |

Nota: las adaptaciones hispanas de APA difieren en `y`/`&`; por eso esos checks son
`menor` (consejo, nunca bloquea). Todo el módulo es **advisory** — la verificación de
citas no bloquea nada en ningún tier (a diferencia del modo estricto de coherencia).

## 5. Verificación de existencia (anti-alucinación)

Cliente async (`httpx`) con dos fuentes, consultadas en paralelo:

- **Crossref:** `GET api.crossref.org/works?query.author={surname}&filter=from-pub-date:{y}-01-01,until-pub-date:{y}-12-31&rows=5&mailto={CONTACT_EMAIL}`
- **OpenAlex:** `GET api.openalex.org/works?search={surname}&filter=publication_year:{y}&per-page=5`

Match = apellido del primer autor de algún resultado coincide con el citado
(case-insensitive, sin diacríticos). Estados:

| Estado | Significado | UI |
|---|---|---|
| `encontrada` | ≥1 obra con autor/año coincidente; se guardan hasta 3 candidatos (título, DOI, año) | 🟢 + links DOI |
| `no_encontrada` | Ambas fuentes respondieron y ninguna tiene match | ⚠ "posible cita inventada" |
| `no_verificable` | Ambas fuentes fallaron/timeout, o cita `s.f.` | ⚪ "no se pudo verificar" |

**Fail-closed honesto:** un fallo de red NUNCA se reporta como "inventada".
Timeout por fuente: 8 s. Sin retries (el usuario puede re-ejecutar).

**Caché:** tabla `citation_lookups` con clave `(surname_normalizado, year)`, JSON de
candidatos, `fetched_at`; TTL 30 días. Evita repetir búsquedas entre ejecuciones y
entre usuarios.

**Anti-abuso:** se añade un limitador en memoria por proyecto (10 ejecuciones/min, `entitlements/ratelimit.py`).
Las búsquedas externas no consumen cuota LLM mensual.

## 6. Capa LLM (híbrida, tier-gated)

- **free:** solo determinista + lookup. Sin costo LLM.
- **pro / doctoral / university:** además, 1 llamada LLM por ejecución (no por cita):
  recibe el contenido de los nodos con citas + las citas extraídas, devuelve contrato
  Pydantic `CitationStyleReview{issues: list[Issue], summary: str}` con matices de estilo
  APA-7 que el regex no cubre (orden cronológico en citas múltiples, citas secundarias
  "citado en", etc.). Reusa por completo `llm_gateway` (instructor, breaker, budget
  diario, taxonomía de errores) y **consume 1 validación de la cuota mensual** del tier.
- Si el LLM falla (timeout/budget/breaker): la ejecución **degrada** — devuelve la parte
  determinista + lookup con `llm_review: null` y un aviso; no aborta (a diferencia del
  Coherence Engine, aquí el LLM es complemento, no veredicto).

## 7. Modelo de datos y API

```
verification/
  extraction.py      # extract_citations(node_type, content) -> list[Citation]
  apa_checks.py      # run_apa_checks(citations, today) -> list[ApaIssue]
  lookup.py          # LookupClient protocol + CrossrefOpenAlexClient + cache
  contracts.py       # CitationStyleReview (contrato LLM, Pydantic)
  models.py          # CitationRun, CitationFinding, CitationLookup (SQLAlchemy)
  pipeline.py        # verify_citations(...) orquestación
  schemas.py         # VerificationOut
  service.py / router.py
```

- `citation_runs`: id, project_id, user_id, created_at, llm_used, llm_review JSON|null.
- `citation_findings`: id, run_id, node_type, raw_text, surname, year, narrative,
  format_issues JSON, existence_status, candidates JSON.
- `citation_lookups`: surname_norm + year (PK compuesta), candidates JSON, fetched_at.

Endpoints (auth requerida, ownership como en constructor):
- `POST /api/projects/{pid}/verify-citations` → ejecuta y devuelve el run completo.
- `GET  /api/projects/{pid}/verify-citations/latest` → último run persistido (o 404).

Migración Alembic nueva para las 3 tablas.

## 8. Frontend

En `ProjectPage`, junto al panel de validación de coherencia, una sección
**“Verificación de citas”**: botón ejecutar, agrupación por nodo, por cita:
badge de formato (issues o ✓) y badge de existencia (🟢 con hasta 3 candidatos
linkeados por DOI / ⚠ posible inventada / ⚪ no verificable). Estado del run LLM
(resumen de estilo) cuando exista. Tipos espejo en `api/types.ts`.

## 9. Testing

- **Unit (CI):** extracción (todas las variantes de §3 + negativos), checks APA (§4),
  mapeo de estados de lookup con `httpx.MockTransport` (éxito, vacío, timeout, 500,
  una fuente caída), caché (hit/miss/TTL).
- **Integración (CI):** endpoint con `FakeLookupClient` + `FakeGateway` inyectados:
  run feliz, proyecto ajeno → 404, free tier sin LLM, LLM caído → degradación,
  rate-limit.
- **Evals (NO CI):** casos dorados de citas reales vs inventadas contra las APIs vivas,
  en `tests/evals/` junto a los existentes.

## 10. Config nueva (`config.py`)

| Setting | Default |
|---|---|
| `lookup_timeout_s` | 8.0 |
| `lookup_cache_ttl_days` | 30 |
| `crossref_mailto` | `admin@srv1533829.hstgr.cloud` |
| `citation_llm_tiers` | pro, doctoral, university |
