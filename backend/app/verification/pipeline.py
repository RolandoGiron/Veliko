from dataclasses import asdict
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN, NodeType
from app.entitlements.errors import QuotaExceeded
from app.entitlements.quota import consume_monthly_quota
from app.entitlements.tiers import Tier, TIER_CONFIG
from app.i18n.prompts import CITATION_SYSTEM_PROMPT_ES, build_citation_prompt
from app.llm_gateway.errors import LLMError
from app.verification.apa_checks import run_apa_checks
from app.verification.contracts import CitationStyleReview
from app.verification.extraction import Citation, extract_citations
from app.verification.lookup import (
    ExistenceStatus,
    LookupClient,
    LookupResult,
    cached_lookup,
)
from app.verification.models import CitationFinding, CitationRun

LLM_TIERS = {Tier.pro, Tier.doctoral, Tier.university}


async def verify_citations(
    session: AsyncSession,
    *,
    lookup_client: LookupClient,
    gateway,
    user_id: str,
    tier: str,
    project_id: str,
    today: date,
) -> tuple[CitationRun, list[CitationFinding]]:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise LookupError("project not found")
    res = await session.scalars(select(Node).where(Node.project_id == project_id))
    nodes = {NodeType(n.type): n for n in res}

    # 1 — deterministic extraction + APA checks (free)
    citations: list[Citation] = []
    for nt in DEPENDENCY_CHAIN:
        node = nodes.get(nt)
        if node is not None:
            citations.extend(extract_citations(nt, node.content))
    issues = run_apa_checks(citations, today)
    project_issues = [asdict(i) for i in issues if i.citation_raw is None]
    by_citation: dict[str, list[dict]] = {}
    for i in issues:
        if i.citation_raw:
            by_citation.setdefault(i.citation_raw, []).append(asdict(i))

    run = CitationRun(project_id=project_id, user_id=user_id,
                      project_issues=project_issues)
    session.add(run)
    await session.flush()

    # 2 — existence lookup (free external APIs, cached, deduped per run)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    seen: dict[tuple[str, int], LookupResult] = {}
    findings: list[CitationFinding] = []
    for c in citations:
        if c.year[:4].isdigit():
            key = (c.surname, int(c.year[:4]))
            if key not in seen:
                seen[key] = await cached_lookup(
                    session, lookup_client, c.surname, key[1],
                    now=now, ttl_days=settings.lookup_cache_ttl_days,
                )
            result = seen[key]
        else:  # s.f. — sin año no hay búsqueda útil
            result = LookupResult(status=ExistenceStatus.no_verificable)
        findings.append(CitationFinding(
            run_id=run.id, node_type=c.node_type.value, raw=c.raw,
            surname=c.surname, year=c.year, narrative=c.narrative,
            format_issues=by_citation.get(c.raw, []),
            existence_status=result.status.value,
            candidates=[asdict(cd) for cd in result.candidates],
        ))
    session.add_all(findings)

    # 3 — LLM style review (paid tiers; degrades, never aborts)
    if citations and Tier(tier) in LLM_TIERS:
        try:
            await _llm_review(session, run, gateway, user_id, tier, nodes,
                              citations, today)
        except QuotaExceeded:
            run.llm_message = (
                "Cuota mensual de validaciones agotada; revisión LLM omitida."
            )
        except LLMError:
            run.llm_message = (
                "El juez de estilo no está disponible ahora; "
                "los resultados deterministas están completos."
            )

    await session.commit()
    await session.refresh(run)
    return run, findings


async def _llm_review(
    session: AsyncSession,
    run: CitationRun,
    gateway,
    user_id: str,
    tier: str,
    nodes: dict[NodeType, Node],
    citations: list[Citation],
    today: date,
) -> None:
    node_ids = await session.scalars(
        select(Node.id)
        .join(ResearchProject, ResearchProject.id == Node.project_id)
        .where(ResearchProject.user_id == user_id)
    )
    await consume_monthly_quota(session, user_id=user_id,
                                node_ids=list(node_ids), tier=tier)

    settings = get_settings()
    cfg = TIER_CONFIG[Tier(tier)]
    model = cfg.anthropic_model if settings.llm_provider == "anthropic" else cfg.openai_model
    cited_nodes = {c.node_type for c in citations}
    contents = {nt: nodes[nt].content for nt in DEPENDENCY_CHAIN
                if nt in cited_nodes and nt in nodes}

    result = gateway.validate(
        model=model,
        system_prompt=CITATION_SYSTEM_PROMPT_ES,
        user_prompt=build_citation_prompt(contents, [c.raw for c in citations]),
        today=today,
        response_model=CitationStyleReview,
    )
    review: CitationStyleReview = result.verdict
    run.llm_used = True
    run.llm_summary = review.summary
    run.llm_issues = [i.model_dump() for i in review.issues]
