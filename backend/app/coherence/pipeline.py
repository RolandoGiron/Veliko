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
    except LLMError:
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
