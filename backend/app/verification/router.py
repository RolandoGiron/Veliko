from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.coherence.service import get_gateway
from app.db import get_session
from app.entitlements.errors import RateLimited
from app.entitlements.ratelimit import SlidingWindowLimiter
from app.verification import pipeline
from app.verification.errors import ProjectNotFound
from app.verification.models import CitationFinding, CitationRun
from app.verification.schemas import CandidateOut, CitationRunOut, FindingOut
from app.verification.service import get_latest_run, get_lookup_client

router = APIRouter(prefix="/api/projects", tags=["verification"])

_limiter = SlidingWindowLimiter(max_events=10, window_s=60.0)


def _to_out(run: CitationRun, findings: list[CitationFinding]) -> CitationRunOut:
    return CitationRunOut(
        id=run.id,
        created_at=run.created_at.isoformat(),
        project_issues=run.project_issues,
        llm_used=run.llm_used,
        llm_summary=run.llm_summary,
        llm_issues=run.llm_issues,
        llm_message=run.llm_message,
        findings=[
            FindingOut(
                node_type=f.node_type, raw=f.raw, surname=f.surname, year=f.year,
                narrative=f.narrative, format_issues=f.format_issues,
                existence_status=f.existence_status,
                candidates=[CandidateOut(**c) for c in f.candidates],
            )
            for f in findings
        ],
    )


@router.post("/{project_id}/verify-citations", response_model=CitationRunOut)
async def verify_citations(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    lookup_client=Depends(get_lookup_client),
    gateway=Depends(get_gateway),
):
    try:
        _limiter.check(project_id)
    except RateLimited:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "demasiadas verificaciones; espera un minuto")
    try:
        run, findings = await pipeline.verify_citations(
            session, lookup_client=lookup_client, gateway=gateway,
            user_id=user.id, tier=user.tier, project_id=project_id,
            today=datetime.now(timezone.utc).date(),
        )
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return _to_out(run, findings)


@router.get("/{project_id}/verify-citations/latest", response_model=CitationRunOut)
async def latest_run(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        found = await get_latest_run(session, user.id, project_id)
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no runs yet")
    return _to_out(*found)
