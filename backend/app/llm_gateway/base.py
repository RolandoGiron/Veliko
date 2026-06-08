from dataclasses import dataclass
from typing import Protocol

from app.coherence.contracts import CoherenceVerdict


@dataclass(frozen=True)
class LLMResult:
    verdict: CoherenceVerdict
    model_used: str
    tokens_used: int
    cost_usd: float


class LLMProvider(Protocol):
    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float
    ) -> LLMResult:
        """Call the model and return a parsed verdict + usage. Raises gateway errors."""
        ...
