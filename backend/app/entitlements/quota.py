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
    from app.verification.models import CitationRun  # local import: avoid cycles

    citation_runs = await session.scalar(
        select(func.count())
        .select_from(CitationRun)
        .where(
            CitationRun.user_id == user_id,
            CitationRun.llm_used.is_(True),
            CitationRun.created_at >= start,
        )
    )
    if (used or 0) + (citation_runs or 0) >= limit:
        raise QuotaExceeded(f"monthly quota {limit} reached for tier {tier}")
