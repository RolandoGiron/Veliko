from datetime import date

from app.llm_gateway.errors import BudgetExceeded


class DailyBudget:
    """In-process daily spend tracker / kill switch.

    Single-process MVP. If the backend later runs multiple workers, move this
    counter to Postgres or Redis. The interface stays identical.
    """

    def __init__(self, limit_usd: float) -> None:
        self._limit = limit_usd
        self._day: date | None = None
        self._spent = 0.0

    def _roll(self, today: date) -> None:
        if self._day != today:
            self._day = today
            self._spent = 0.0

    def ensure_within_budget(self, today: date) -> None:
        self._roll(today)
        if self._spent >= self._limit:
            raise BudgetExceeded(f"daily budget {self._limit} reached")

    def record(self, cost_usd: float, today: date) -> None:
        self._roll(today)
        self._spent += cost_usd
