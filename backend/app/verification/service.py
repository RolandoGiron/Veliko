from functools import lru_cache

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constructor.models import ResearchProject
from app.verification.errors import ProjectNotFound
from app.verification.lookup import CrossrefOpenAlexClient, LookupClient
from app.verification.models import CitationFinding, CitationRun


@lru_cache
def _singleton_client() -> CrossrefOpenAlexClient:
    s = get_settings()
    return CrossrefOpenAlexClient(
        httpx.AsyncClient(), mailto=s.crossref_mailto, timeout_s=s.lookup_timeout_s
    )


def get_lookup_client() -> LookupClient:
    """FastAPI dependency; overridden in tests with a fake."""
    return _singleton_client()


async def get_latest_run(
    session: AsyncSession, user_id: str, project_id: str
) -> tuple[CitationRun, list[CitationFinding]] | None:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise ProjectNotFound("project not found")
    run = await session.scalar(
        select(CitationRun)
        .where(CitationRun.project_id == project_id)
        .order_by(CitationRun.created_at.desc())
        .limit(1)
    )
    if run is None:
        return None
    findings = list(await session.scalars(
        select(CitationFinding).where(CitationFinding.run_id == run.id)
    ))
    return run, findings
