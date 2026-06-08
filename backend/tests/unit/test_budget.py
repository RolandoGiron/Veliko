from datetime import date

import pytest

from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.errors import BudgetExceeded


def test_under_budget_allows():
    b = DailyBudget(limit_usd=1.0)
    b.ensure_within_budget(today=date(2026, 6, 7))  # no spend yet
    b.record(0.40, today=date(2026, 6, 7))
    b.ensure_within_budget(today=date(2026, 6, 7))


def test_over_budget_blocks():
    b = DailyBudget(limit_usd=1.0)
    b.record(1.20, today=date(2026, 6, 7))
    with pytest.raises(BudgetExceeded):
        b.ensure_within_budget(today=date(2026, 6, 7))


def test_budget_resets_next_day():
    b = DailyBudget(limit_usd=1.0)
    b.record(1.20, today=date(2026, 6, 7))
    # new day -> spend resets, allowed again
    b.ensure_within_budget(today=date(2026, 6, 8))
