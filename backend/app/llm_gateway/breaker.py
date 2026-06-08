from app.llm_gateway.errors import LLMUnavailable


class CircuitBreaker:
    def __init__(self, threshold: int, cooldown_s: float) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_s
        self._failures = 0
        self._opened_at: float | None = None

    def ensure_closed(self, now: float) -> None:
        if self._opened_at is None:
            return
        if now - self._opened_at >= self._cooldown:
            # half-open: allow a trial call, keep counters until it resolves
            return
        raise LLMUnavailable("circuit open")

    def record_failure(self, now: float) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = now

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
