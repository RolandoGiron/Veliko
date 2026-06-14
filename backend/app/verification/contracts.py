from typing import Literal

from pydantic import BaseModel

Severity = Literal["critica", "mayor", "menor"]


class StyleIssue(BaseModel):
    severity: Severity
    code: str               # snake_case corto, p.ej. "orden_cronologico"
    message: str            # en español
    citation: str | None = None


class CitationStyleReview(BaseModel):
    issues: list[StyleIssue]
    summary: str
