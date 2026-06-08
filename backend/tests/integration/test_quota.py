import pytest
from datetime import datetime, timezone

from app.coherence.models import ValidationResult
from app.entitlements.errors import QuotaExceeded
from app.entitlements.quota import consume_monthly_quota


@pytest.mark.asyncio
async def test_quota_counts_this_month_and_blocks_over_limit(db_session):
    # tier free => limit 20; insert 20 results this month
    now = datetime.now(timezone.utc)
    for _ in range(20):
        db_session.add(
            ValidationResult(
                node_id="n", score=80, issues=[], suggestions=[],
                model_used="m", tokens_used=1, cost_usd=0.0, created_at=now,
            )
        )
    await db_session.commit()

    with pytest.raises(QuotaExceeded):
        await consume_monthly_quota(db_session, user_id="u", node_ids=["n"], tier="free")


@pytest.mark.asyncio
async def test_quota_allows_when_under_limit(db_session):
    # no prior results -> allowed
    await consume_monthly_quota(db_session, user_id="u", node_ids=["n"], tier="free")
