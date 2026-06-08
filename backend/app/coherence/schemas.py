from pydantic import BaseModel

from app.coherence.contracts import Issue


class ValidationOut(BaseModel):
    status: str                 # PipelineOutcome value
    score: int | None = None
    issues: list[Issue] = []
    suggestions: list[str] = []
    summary: str | None = None
    mode: str | None = None     # asesor | estricto
    blocked: bool = False
    message: str | None = None  # for precheck/llm-failure user messaging
    node_state: str | None = None
