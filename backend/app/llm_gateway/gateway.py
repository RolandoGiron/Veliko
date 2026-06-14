import time
from datetime import date

from pydantic import BaseModel

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMProvider, LLMResult
from app.llm_gateway.budget import DailyBudget
from app.llm_gateway.breaker import CircuitBreaker
from app.llm_gateway.errors import LLMTimeout, LLMUnavailable


class LLMGateway:
    def __init__(
        self,
        provider: LLMProvider,
        budget: DailyBudget,
        breaker: CircuitBreaker,
        timeout_s: float,
    ) -> None:
        self._provider = provider
        self._budget = budget
        self._breaker = breaker
        self._timeout_s = timeout_s

    def validate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        today: date,
        response_model: type[BaseModel] = CoherenceVerdict,
    ) -> LLMResult:
        self._budget.ensure_within_budget(today)
        self._breaker.ensure_closed(now=time.monotonic())

        try:
            result = self._call_with_one_retry(
                model, system_prompt, user_prompt, response_model
            )
        except (LLMUnavailable, LLMTimeout):
            self._breaker.record_failure(now=time.monotonic())
            raise

        self._breaker.record_success()
        self._budget.record(result.cost_usd, today)
        return result

    def _call_with_one_retry(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> LLMResult:
        try:
            return self._provider.validate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_s=self._timeout_s,
                response_model=response_model,
            )
        except LLMTimeout:
            time.sleep(0.5)  # simple backoff; one retry
            return self._provider.validate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_s=self._timeout_s,
                response_model=response_model,
            )
