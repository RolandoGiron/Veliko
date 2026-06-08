from functools import lru_cache

from app.config import get_settings
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.gateway import LLMGateway
from app.llm_gateway.providers.anthropic_provider import AnthropicProvider
from app.llm_gateway.providers.openai_provider import OpenAIProvider


@lru_cache
def _singleton_gateway() -> LLMGateway:
    s = get_settings()
    if s.llm_provider == "openai":
        provider = OpenAIProvider(api_key=s.openai_api_key)
    else:
        provider = AnthropicProvider(api_key=s.anthropic_api_key)
    return LLMGateway(
        provider=provider,
        budget=DailyBudget(limit_usd=s.daily_budget_usd),
        breaker=CircuitBreaker(s.circuit_breaker_threshold, s.circuit_breaker_cooldown_s),
        timeout_s=s.llm_timeout_s,
    )


def get_gateway() -> LLMGateway:
    """FastAPI dependency; overridden in tests with a fake."""
    return _singleton_gateway()
