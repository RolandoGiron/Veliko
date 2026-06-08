import anthropic
import instructor

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import (
    LLMRateLimit,
    LLMTimeout,
    LLMUnavailable,
    LLMUnparseable,
)

# USD per 1M tokens (approx; tune from billing). input/output blended is fine for MVP.
_PRICES = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
}


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _PRICES.get(model, (3.0, 15.0))
    return (in_tok * pin + out_tok * pout) / 1_000_000


class AnthropicProvider:
    def __init__(self, api_key: str) -> None:
        self._client = instructor.from_anthropic(anthropic.Anthropic(api_key=api_key))

    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float
    ) -> LLMResult:
        try:
            verdict, completion = self._client.chat.completions.create_with_completion(
                model=model,
                max_tokens=1500,
                system=[{"type": "text", "text": system_prompt,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_prompt}],
                response_model=CoherenceVerdict,
                max_retries=2,
                timeout=timeout_s,
            )
        except anthropic.APITimeoutError as e:
            raise LLMTimeout(str(e)) from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimit(str(e)) from e
        except anthropic.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailable(str(e)) from e
            raise
        except instructor.exceptions.InstructorRetryException as e:
            raise LLMUnparseable(str(e)) from e

        usage = completion.usage
        in_tok = getattr(usage, "input_tokens", 0)
        out_tok = getattr(usage, "output_tokens", 0)
        return LLMResult(
            verdict=verdict,
            model_used=model,
            tokens_used=in_tok + out_tok,
            cost_usd=_cost(model, in_tok, out_tok),
        )
