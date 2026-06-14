from datetime import date

import pytest

from app.auth.models import User
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import LLMTimeout
from app.verification.contracts import CitationStyleReview
from app.verification.lookup import ExistenceStatus, LookupResult
from app.verification.pipeline import verify_citations

TODAY = date(2026, 6, 11)


class FakeLookup:
    def __init__(self, status=ExistenceStatus.encontrada):
        self.calls: list[tuple[str, int]] = []
        self._status = status

    async def lookup(self, surname: str, year: int) -> LookupResult:
        self.calls.append((surname, year))
        return LookupResult(status=self._status)


class FakeGateway:
    def __init__(self, raises=None):
        self.called = False
        self._raises = raises

    def validate(self, *, model, system_prompt, user_prompt, today,
                 response_model=None):
        self.called = True
        if self._raises:
            raise self._raises
        return LLMResult(
            verdict=CitationStyleReview(issues=[], summary="Estilo correcto."),
            model_used=model, tokens_used=10, cost_usd=0.001,
        )


async def _seed(db_session, tier="pro", content="Según García (2020), hay un vacío."):
    user = User(email="t@v.com", password_hash="x", tier=tier)
    db_session.add(user)
    await db_session.flush()
    project = ResearchProject(user_id=user.id, title="T")
    db_session.add(project)
    await db_session.flush()
    for nt in DEPENDENCY_CHAIN:
        db_session.add(Node(project_id=project.id, type=nt.value,
                            content=content if nt.value == "problema" else ""))
    await db_session.commit()
    return user, project


@pytest.mark.asyncio
async def test_happy_path_pro_tier_uses_llm(db_session):
    user, project = await _seed(db_session)
    lookup, gw = FakeLookup(), FakeGateway()
    run, findings = await verify_citations(
        db_session, lookup_client=lookup, gateway=gw,
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert len(findings) == 1
    assert findings[0].surname == "García"
    assert findings[0].existence_status == "encontrada"
    assert lookup.calls == [("García", 2020)]
    assert gw.called and run.llm_used is True
    assert run.llm_summary == "Estilo correcto."


@pytest.mark.asyncio
async def test_free_tier_skips_llm(db_session):
    user, project = await _seed(db_session, tier="free")
    gw = FakeGateway()
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(), gateway=gw,
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert gw.called is False and run.llm_used is False
    assert len(findings) == 1


@pytest.mark.asyncio
async def test_llm_failure_degrades_not_aborts(db_session):
    user, project = await _seed(db_session)
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(),
        gateway=FakeGateway(raises=LLMTimeout("slow")),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert run.llm_used is False
    assert run.llm_message is not None
    assert len(findings) == 1  # deterministic part intact


@pytest.mark.asyncio
async def test_not_found_marks_possible_hallucination(db_session):
    user, project = await _seed(db_session, tier="free")
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(ExistenceStatus.no_encontrada),
        gateway=FakeGateway(), user_id=user.id, tier=user.tier,
        project_id=project.id, today=TODAY,
    )
    assert findings[0].existence_status == "no_encontrada"


@pytest.mark.asyncio
async def test_sf_citation_not_looked_up(db_session):
    user, project = await _seed(db_session, tier="free",
                                content="Lo afirma (López, s.f.).")
    lookup = FakeLookup()
    run, findings = await verify_citations(
        db_session, lookup_client=lookup, gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert lookup.calls == []
    assert findings[0].existence_status == "no_verificable"


@pytest.mark.asyncio
async def test_no_citations_project_issue(db_session):
    user, project = await _seed(db_session, tier="free", content="Sin citas aquí pero largo.")
    run, findings = await verify_citations(
        db_session, lookup_client=FakeLookup(), gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert findings == []
    assert any(i["code"] == "sin_citas" for i in run.project_issues)
    assert run.llm_used is False  # no citations -> no LLM even on pro


@pytest.mark.asyncio
async def test_other_users_project_raises(db_session):
    user, project = await _seed(db_session)
    with pytest.raises(LookupError):
        await verify_citations(
            db_session, lookup_client=FakeLookup(), gateway=FakeGateway(),
            user_id="someone-else", tier="pro", project_id=project.id, today=TODAY,
        )


@pytest.mark.asyncio
async def test_duplicate_citation_looked_up_once(db_session):
    user, project = await _seed(
        db_session, tier="free",
        content="García (2020) lo dijo; lo repite (García, 2020).",
    )
    lookup = FakeLookup()
    await verify_citations(
        db_session, lookup_client=lookup, gateway=FakeGateway(),
        user_id=user.id, tier=user.tier, project_id=project.id, today=TODAY,
    )
    assert lookup.calls == [("García", 2020)]
