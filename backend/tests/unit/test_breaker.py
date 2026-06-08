import pytest

from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import LLMUnavailable


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(threshold=3, cooldown_s=60)
    for _ in range(3):
        cb.record_failure(now=0.0)
    with pytest.raises(LLMUnavailable):
        cb.ensure_closed(now=1.0)


def test_success_resets_failures():
    cb = CircuitBreaker(threshold=3, cooldown_s=60)
    cb.record_failure(now=0.0)
    cb.record_failure(now=0.0)
    cb.record_success()
    cb.record_failure(now=0.0)
    cb.ensure_closed(now=1.0)  # only 1 failure since reset -> still closed


def test_closes_again_after_cooldown():
    cb = CircuitBreaker(threshold=2, cooldown_s=60)
    cb.record_failure(now=0.0)
    cb.record_failure(now=0.0)
    with pytest.raises(LLMUnavailable):
        cb.ensure_closed(now=10.0)
    cb.ensure_closed(now=61.0)  # cooldown elapsed -> allowed (half-open)
