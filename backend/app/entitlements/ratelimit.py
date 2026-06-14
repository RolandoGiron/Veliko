import time

from app.entitlements.errors import RateLimited


class SlidingWindowLimiter:
    """In-memory per-key sliding window. Single-process MVP scope."""

    def __init__(self, max_events: int, window_s: float) -> None:
        self._max = max_events
        self._window = window_s
        self._events: dict[str, list[float]] = {}

    def check(self, key: str, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        events = [e for e in self._events.get(key, []) if e > t - self._window]
        if len(events) >= self._max:
            self._events[key] = events
            raise RateLimited(f"max {self._max} events per {self._window}s")
        events.append(t)
        self._events[key] = events
