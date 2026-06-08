from datetime import date

import pytest

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import BudgetExceeded, LLMTimeout, LLMUnavailable
from app.llm_gateway.gateway import LLMGateway


class FakeProvider:
    def __init__(self, *, raises=None, calls_to_fail=0):
        self.calls = 0
        self._raises = raises
        self._calls_to_fail = calls_to_fail

    def validate(self, *, model, system_prompt, user_prompt, timeout_s):
        self.calls += 1
        if self._raises and self.calls <= self._calls_to_fail:
            raise self._raises
        return LLMResult(
            verdict=CoherenceVerdict(score=88, issues=[], suggestions=[], summary="ok"),
            model_used=model,
            tokens_used=100,
            cost_usd=0.01,
        )


def _gateway(provider, *, budget=10.0, threshold=5):
    return LLMGateway(
        provider=provider,
        budget=DailyBudget(limit_usd=budget),
        breaker=CircuitBreaker(threshold=threshold, cooldown_s=60),
        timeout_s=30.0,
    )


def test_happy_path_returns_result_and_records_cost():
    p = FakeProvider()
    gw = _gateway(p)
    res = gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert res.verdict.score == 88
    assert p.calls == 1


def test_timeout_retries_once_then_succeeds():
    p = FakeProvider(raises=LLMTimeout("slow"), calls_to_fail=1)
    gw = _gateway(p)
    res = gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert res.verdict.score == 88
    assert p.calls == 2  # one failed, one retry succeeded


def test_timeout_twice_raises():
    p = FakeProvider(raises=LLMTimeout("slow"), calls_to_fail=2)
    gw = _gateway(p)
    with pytest.raises(LLMTimeout):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))


def test_budget_blocks_before_calling_provider():
    p = FakeProvider()
    gw = _gateway(p, budget=0.0)
    with pytest.raises(BudgetExceeded):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert p.calls == 0


def test_breaker_opens_after_repeated_unavailable():
    p = FakeProvider(raises=LLMUnavailable("5xx"), calls_to_fail=99)
    gw = _gateway(p, threshold=2)
    for _ in range(2):
        with pytest.raises(LLMUnavailable):
            gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    calls_before = p.calls
    with pytest.raises(LLMUnavailable):
        gw.validate(model="m", system_prompt="s", user_prompt="u", today=date(2026, 6, 7))
    assert p.calls == calls_before  # breaker open -> provider not called
