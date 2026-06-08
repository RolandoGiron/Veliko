class LLMError(Exception):
    """Base for all gateway failures."""


class LLMTimeout(LLMError):
    pass


class LLMRateLimit(LLMError):
    pass


class LLMUnavailable(LLMError):
    """Provider 5xx / circuit breaker open."""


class LLMUnparseable(LLMError):
    """Model never produced a valid CoherenceVerdict."""


class BudgetExceeded(LLMError):
    pass
