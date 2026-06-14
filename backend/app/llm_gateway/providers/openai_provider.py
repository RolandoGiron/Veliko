import instructor
import openai

from app.coherence.contracts import CoherenceVerdict
from app.llm_gateway.base import LLMResult
from app.llm_gateway.errors import (
    LLMRateLimit,
    LLMTimeout,
    LLMUnavailable,
    LLMUnparseable,
)

_PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
}


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _PRICES.get(model, (2.50, 10.0))
    return (in_tok * pin + out_tok * pout) / 1_000_000


class OpenAIProvider:
    def __init__(self, api_key: str) -> None:
        self._client = instructor.from_openai(openai.OpenAI(api_key=api_key))

    def validate(
        self, *, model: str, system_prompt: str, user_prompt: str, timeout_s: float,
        response_model: type = None,
    ) -> LLMResult:
        try:
            verdict, completion = self._client.chat.completions.create_with_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=response_model or CoherenceVerdict,
                max_retries=2,
                timeout=timeout_s,
            )
        except openai.APITimeoutError as e:
            raise LLMTimeout(str(e)) from e
        except openai.RateLimitError as e:
            raise LLMRateLimit(str(e)) from e
        except openai.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailable(str(e)) from e
            raise
        except instructor.exceptions.InstructorRetryException as e:
            raise LLMUnparseable(str(e)) from e

        usage = completion.usage
        in_tok = getattr(usage, "prompt_tokens", 0)
        out_tok = getattr(usage, "completion_tokens", 0)
        return LLMResult(
            verdict=verdict,
            model_used=model,
            tokens_used=in_tok + out_tok,
            cost_usd=_cost(model, in_tok, out_tok),
        )
