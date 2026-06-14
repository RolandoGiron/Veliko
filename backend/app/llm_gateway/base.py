from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMResult:
    verdict: BaseModel  # instance of the requested response_model
    model_used: str
    tokens_used: int
    cost_usd: float


class LLMProvider(Protocol):
    def validate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout_s: float,
        response_model: type[BaseModel],
    ) -> LLMResult:
        """Call the model and return a parsed verdict + usage. Raises gateway errors."""
        ...
