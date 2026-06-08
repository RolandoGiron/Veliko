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
