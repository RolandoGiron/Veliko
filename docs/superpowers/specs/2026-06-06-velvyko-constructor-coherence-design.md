# Velvyko — Spec de diseño: Constructor + Coherence Engine (MVP)

- **Fecha:** 2026-06-06
- **Autor:** Mario García Girón (Founder & CEO / cofundador técnico)
- **Subsistema:** Constructor Inteligente de Investigación + Scientific Coherence Engine
- **Estado:** Diseño aprobado — plan de implementación en `docs/superpowers/plans/2026-06-07-velvyko-constructor-coherence.md`
- **Revisión de infra (2026-06-08):** topología verificada en vivo sobre el VPS (shell + MCPs Hostinger/n8n). Decisiones D7/D8 y §4 ajustadas a la realidad confirmada (Traefik, red `clinic-net`, Postgres dedicado con pgvector). Ver §4 y §11.

---

## 1. Contexto

Velvyko es una plataforma SaaS de "Inteligencia Metodológica Científica" para
educación superior (maestrandos, doctorandos, investigadores, universidades). Su
diferenciador no es *generar texto* sino **fortalecer el razonamiento científico**
y la consistencia metodológica (problema → hipótesis → variables → instrumentos).

Este spec cubre **únicamente el primer subsistema** a construir: el Constructor +
Coherence Engine, identificado como la feature estrella del MVP (las demás —
Doctoral Attack Mode™, APA Validation, DOI Verification — operan *sobre* lo que
este subsistema produce, y tendrán sus propios specs).

### Restricción de infraestructura
Despliegue inicial en un único VPS de **8 GB de RAM** (`srv1533829`, 72.60.126.116)
que **ya** ejecuta un stack de producción (n8n, evolution-api/WhatsApp, un Postgres
de la clínica, Traefik, Redis) consumiendo **~3.2–3.6 GB** hoy (verificado
2026-06-08). Margen real para Velvyko: ~1–1.5 GB. El proxy (Traefik) y la red
Docker compartida (`clinic-net`) ya existen y se reutilizan.

---

## 2. Decisiones de diseño (registro)

| # | Decisión | Elección |
|---|----------|----------|
| D1 | LLM de razonamiento | **API hospedada** (Claude/GPT) en el MVP. Auto-hospedaje (Ollama) descartado para MVP: inviable en 8 GB y degradaría el rigor. Se reevalúa post-MVP con GPU dedicada. |
| D2 | Feature estrella del MVP | **Constructor + Coherence Engine** |
| D3 | Modelo de interacción | **Híbrido**: wizard guiado con saltos a cualquier nodo → implica validación en cascada |
| D4 | Comportamiento de validación | **Asesor por defecto** (puntúa+sugiere, nunca bloquea); **modo estricto** (bloqueante por umbral) para el tier **Doctoral** |
| D5 | Rol de la IA frente al texto | **Solo valida y sugiere; el usuario escribe.** La IA puede sugerir mejoras pero NUNCA redacta el contenido original |
| D6 | Idioma | **Español** en el MVP, arquitectura **i18n-ready** (inglés sin refactor) |
| D7 | Stack | **Enfoque A — monolito modular**: React (Vite) SPA · Python + FastAPI · Postgres + pgvector · gateway LLM swappable · Docker Compose. Proxy = **Traefik existente** (vía labels); Caddy solo para dev local |
| D8 | Reutilización de infra | **Postgres dedicado** `pgvector/pgvector:pg16` (contenedor `velvyko-postgres`, DB `velvyko`) sobre la red `clinic-net`. *Corrección 2026-06-08:* el Postgres existente (`postgres:16-alpine`, propiedad del stack de la clínica) **no trae pgvector** y aislar los datos es más seguro → no se reutiliza. Se reutilizan **Traefik** (proxy/TLS) y la red `clinic-net`. **n8n** (ya corriendo) solo para periferia (emails, tareas programadas, evals, webhooks), NUNCA para la lógica central |

---

## 3. Alcance

**Dentro del MVP (este spec):**
- Gestión de proyectos de investigación con 6 nodos metodológicos.
- Edición de nodos (el usuario escribe el contenido).
- Validación de coherencia por nodo a demanda (LLM-juez con salida estructurada).
- Validación en cascada (estados de frescura por hash).
- Gate asesor/estricto según tier.
- Tracking de costo y guardrails.

**Fuera del MVP (specs futuros):**
- Doctoral Attack Mode™, APA Validation, DOI Verification, Scientific Memory (RAG).
- Billing real / pasarela de pagos (solo se modela el campo `tier`).
- Multi-idioma activo (solo se deja la arquitectura lista).
- Estructura fina de nodos (objetivos múltiples, operacionalización de variables).

---

## 4. Sección 1 — Arquitectura general y topología

Monolito modular desplegado con un único `docker-compose`.

```
                    Internet
                       │
              ┌────────▼─────────┐
              │ Traefik (EXISTE) │  TLS automático (Let's Encrypt)
              │ host-mode, labels│  enruta por labels en clinic-net
              └───┬─────────┬────┘
        Host(velvyko…)      │  Host(velvyko…) && PathPrefix(/api)
        + estáticos         │
                  ▼         ▼
   [ nginx:alpine ]   ┌──────────────┐
   [ React SPA build] │  Backend     │
   (estático)         │  FastAPI     │  (~600 MB, 2 workers)
                      └──────┬───────┘
                             ▼
        ┌──────────────────────────────┐
        │ velvyko-postgres (DEDICADO)   │  pgvector/pgvector:pg16
        │ pgvector listo (memory futuro)│  red clinic-net, volumen propio
        └──────────────────────────────┘
```

### Presupuesto de RAM (8 GB)
| | RAM |
|---|---|
| Stack de producción existente (n8n, evolution, clinic-postgres, Traefik, Redis) | ~3.2–3.6 GB (verificado) |
| Backend Velvyko (FastAPI, 2 workers) | ~600 MB |
| `velvyko-postgres` dedicado (idle) | ~30–50 MB |
| Frontend (nginx estático) | ~10 MB |
| Traefik | ya contado (existente, +0) |
| **Total** | **~3.9–4.3 GB → ~3.7 GB de margen** ✅ |

### Módulos del backend (fronteras limpias)
```
backend/
├── auth/          # usuarios, sesiones
├── entitlements/  # tier (free|pro|doctoral|university) + gates
├── constructor/   # ★ proyecto + grafo de 6 nodos + staleness
├── coherence/     # ★ orquestación del LLM-juez + resultados
├── llm_gateway/   # único módulo que conoce el proveedor de IA;
│                  #   salida estructurada, caching, tracking de costo
├── i18n/          # plantillas de prompts/textos por idioma
└── (futuro) memory/ apa/ doi/ attack_mode/
```

### Reglas de diseño
1. Ningún módulo accede a las tablas de otro; solo a su interfaz pública
   (permite partir un módulo a su propio servicio sin reescribir).
2. `llm_gateway` es el único que conoce el proveedor de IA. El resto pide
   "valida esta coherencia" y recibe un objeto tipado.
3. Todo texto visible y todo prompt vive en `i18n`, parametrizado por idioma.

---

## 5. Sección 2 — Modelo de datos y validación en cascada

### Entidades
```
User
 ├─ id, email, tier (free|pro|doctoral|university)

ResearchProject
 ├─ id, user_id, title, language (es|en), created_at, updated_at

Node                          # 6 nodos metodológicos, 1 por tipo por proyecto
 ├─ id, project_id
 ├─ type    (problema|objetivos|hipotesis|variables|metodologia|instrumentos)
 ├─ content (texto que escribe el usuario)
 ├─ last_validated_hash  (hash de [content propio + contenido de dependencias]
 │                        al momento de la última validación válida)
 └─ updated_at

ValidationResult              # historial auditable + control de costo
 ├─ id, node_id
 ├─ score (0–100), issues[] (jsonb), suggestions[] (jsonb)
 ├─ model_used, tokens_used, cost_usd
 └─ created_at
```

### Cadena de dependencias
```
problema → objetivos → hipotesis → variables → metodologia → instrumentos
```
Al validar un nodo, el motor evalúa su contenido **a la luz de sus dependencias
aguas arriba**.

### Frescura por hash (cascada robusta sin banderas frágiles)
Cada nodo muestra uno de 3 estados, calculados al vuelo:

| Estado | Cálculo | Color |
|--------|---------|-------|
| `sin validar` | nunca tuvo validación | ⚪ |
| `válido` | `hash_actual(content+deps) == last_validated_hash` | 🟢 |
| `obsoleto` | los hashes difieren (editó este nodo o cambió algo aguas arriba) | 🟡 |

**Ejemplo:** editar `problema` lo marca 🟡 y propaga 🟡 a todos sus descendientes
automáticamente (su hash aguas-arriba deja de coincidir). El LLM solo se llama
cuando el usuario decide re-validar.

### Simplificación deliberada (YAGNI)
1 nodo por tipo, `content` como texto rico. La estructura fina (objetivos
múltiples, variable independiente/dependiente) se añade después sin romper el
modelo.

---

## 6. Sección 3 — Flujo del Coherence Engine

Pipeline de 5 pasos; el LLM (paso 3) se evita siempre que se pueda.

```
1. DEDUP POR HASH        → si coincide, devuelve resultado guardado. CERO costo.
2. PRE-CHECKS (sin LLM)  → vacío / muy corto / deps 🟡 → corta sin llamar al LLM.
3. LLM-JUEZ              → única llamada de pago. system_prompt CACHEADO + rúbrica
                           + deps + content. Modelo según tier.
4. SALIDA ESTRUCTURADA   → Pydantic + instructor fuerza el contrato o reintenta.
5. PERSISTIR + GATE      → guarda ValidationResult, actualiza hash (→🟢),
                           entitlements decide asesor vs estricto bloqueante.
```

### Contrato de salida (Pydantic)
```python
class Issue(BaseModel):
    severity: Literal["critica", "mayor", "menor"]
    dimension: Literal["coherencia", "falsabilidad", "claridad",
                       "alineacion_objetivos", "medibilidad"]
    explanation: str          # en español
    location: str | None

class CoherenceVerdict(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: list[Issue]
    suggestions: list[str]    # mejoras; NUNCA reescribe el contenido (D5)
    summary: str
```
Si el modelo no produce un `CoherenceVerdict` válido, `instructor` reintenta con
el error de validación. El backend nunca recibe JSON roto.

### Construcción del prompt
- `system_prompt` = persona "examinador metodológico riguroso" + rúbrica por
  dimensión. Estático y largo → **prompt caching** (solo se paga la parte variable).
- `user_prompt` = dependencias aguas arriba + `content` + tipo de nodo.
- Todo en `i18n`, parametrizado por idioma.

### Modelo por tier
| Tier | Modelo | Razón |
|------|--------|-------|
| Free / Pro | Haiku | crítica sólida y económica para volumen |
| Doctoral (estricto) | Sonnet/Opus | crítica profunda nivel jurado; justifica el precio |

### Cuatro ahorros de costo integrados
dedup por hash · pre-checks sin LLM · prompt caching de la rúbrica · modelo por tier.

---

## 7. Sección 4 — Manejo de errores y modos de fallo

### Principio rector: `fail-closed`, nunca `fail-open`
Si el motor no puede validar con confianza, el nodo **permanece 🟡**. Jamás marca
🟢 ni inventa un score. Preferible "no pude validar" que un falso "todo coherente".

### Mapa de fallos (en `llm_gateway`)
| Fallo | Sistema | Usuario |
|-------|---------|---------|
| Timeout | 1 reintento con backoff; si falla, aborta | "tardó demasiado, reintenta"; nodo sigue 🟡 |
| Rate limit (429) | backoff exponencial + cola | spinner un poco más |
| API caída (5xx) | circuit breaker (pausa 60s tras N fallos) | banner "validación no disponible"; resto funciona |
| Salida no parseable | registra incidente; no inventa score | "no pudimos validar con confianza, reintenta" |
| Presupuesto excedido | bloquea antes de gastar | "alcanzaste tu límite del plan" |

### Guardrails de costo
```
Por usuario:   límite de validaciones/mes según tier
Por proyecto:  rate-limit anti-abuso (máx X validaciones/min)
Global (tú):   kill switch de gasto diario en llm_gateway →
               si el costo del día supera $UMBRAL, degrada a solo-Haiku o
               pausa validaciones y alerta (vía n8n → email)
```

### Veredictos dudosos (calidad)
- El modo asesor por defecto absorbe el riesgo de error del juez.
- Botón "reportar validación injusta" → cola de mejora de rúbrica/prompt.
- Modo estricto usa modelo fuerte para reducir tasa de error.

### Idempotencia y consistencia
- Doble clic → una sola llamada real (dedup por hash).
- `ValidationResult` + `last_validated_hash` se escriben en una transacción.

### Observabilidad mínima
Cada validación registra latencia, modelo, tokens, costo y resultado
(ok/tipo de fallo). Dato necesario para fijar precios de los tiers.

---

## 8. Sección 5 — Estrategia de pruebas

Separar lo determinista (mayoría) de lo no-determinista (solo el juicio del LLM).

```
        ╱╲        EVALS del LLM-juez (pocas, caras, fuera de CI)
       ╱──╲       INTEGRACIÓN (gateway MOCKEADO)
      ╱────╲      UNITARIAS (muchas, rápidas, gratis, deterministas)
     ╱──────╲
```

### Nivel 1 — Unitarias (deterministas, gratis, en cada commit)
- Lógica de cascada/hash (funciones puras).
- Pre-checks deterministas.
- Gate por tier (con `CoherenceVerdict` fijo).
- Parseo APA / DOI (futuro) con APIs externas mockeadas.

### Nivel 2 — Integración (gateway mockeado)
Regla de oro: **en los tests nadie llama al LLM real.** El `llm_gateway` se
reemplaza por un doble que devuelve un `CoherenceVerdict` predefinido.
- Pipeline completo de 5 pasos.
- Todos los modos de fallo de §7 (inyectando excepciones → verificar fail-closed).
- Idempotencia (doble clic → una llamada).

### Nivel 3 — Evals del LLM-juez (separado de CI)
- Dataset dorado: ~20–50 casos `(content+deps → banda de score + dimensión esperada)`.
- Se evalúa con tolerancias/aciertos, no igualdad exacta.
- No corre en cada commit (cuesta dinero, no-determinista); corre al cambiar la
  rúbrica/prompt o periódicamente (vía n8n).
- Defensa anti-regresión de prompts.

### Filosofía
Testea la maquinaria (determinista) exhaustivamente y gratis en CI. Mide la
calidad del juicio (LLM) con evals separados y tolerantes. Nunca los mezcles.

---

## 9. Plan de fases del MVP (referencia)

| Fase | Semanas | Contenido |
|------|---------|-----------|
| 0 — Fundación | 1–2 | Auth, modelo de datos del grafo, shell del dashboard |
| 1 — Constructor + Coherencia | 3–6 | Núcleo determinista + primer LLM-juez (**MVP demostrable**) |
| 2 — Verificación | 7–8 | APA validation + DOI/anti-alucinación (spec aparte) |
| 3 — Attack Mode + tiers | 9–12 | Feature premium + billing (spec aparte) |

## 10. Presupuesto mensual estimado (rangos)

| Partida | Costo |
|---------|-------|
| VPS 8 GB (ya existente) | ~$15–50/mes |
| LLM razonamiento (API) | ~$50–300/mes (variable dominante) |
| APIs bibliográficas (Crossref/OpenAlex) | $0 |
| Base vectorial (pgvector en Postgres) | $0 |
| Email/Auth/Pagos | $0–25/mes |
| **Total MVP** | **~$70–400/mes** |

---

## 11. Preguntas abiertas / a definir antes o durante implementación

- Proveedor de LLM concreto y claves (Anthropic / OpenAI).
- Valores exactos de los guardrails: validaciones/mes por tier, umbral del kill switch diario.
- Umbral de score para el modo estricto (Doctoral).
- Mínimo de palabras de los pre-checks por tipo de nodo.
- ~~¿Reutilizar proxy existente del VPS o desplegar Caddy propio?~~ **RESUELTO (2026-06-08):** reutilizar **Traefik existente** (host-mode, Docker provider, Let's Encrypt) vía labels; Caddy solo dev local.
- ~~Versión de Postgres existente (confirmar soporte pgvector, 13+).~~ **RESUELTO (2026-06-08):** el Postgres existente es `postgres:16-alpine` **sin pgvector** y es de la clínica → Velvyko usa **Postgres dedicado `pgvector/pgvector:pg16`**.
- Librería de auth (propia vs solución como Authentik/Supabase-auth). → *Plan:* JWT propio HS256 (ver Config Defaults del plan).
```
