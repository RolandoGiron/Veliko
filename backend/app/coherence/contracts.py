from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critica", "mayor", "menor"]
Dimension = Literal[
    "coherencia", "falsabilidad", "claridad", "alineacion_objetivos", "medibilidad"
]


class Issue(BaseModel):
    severity: Severity
    dimension: Dimension
    explanation: str            # en español
    location: str | None = None


class CoherenceVerdict(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: list[Issue]
    suggestions: list[str]      # mejoras; NUNCA reescribe el contenido (D5)
    summary: str
