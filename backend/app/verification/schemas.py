from pydantic import BaseModel


class CandidateOut(BaseModel):
    title: str
    doi: str | None
    year: int | None
    source: str


class FindingOut(BaseModel):
    node_type: str
    raw: str
    surname: str
    year: str
    narrative: bool
    format_issues: list[dict]
    existence_status: str
    candidates: list[CandidateOut]


class CitationRunOut(BaseModel):
    id: str
    created_at: str
    project_issues: list[dict]
    llm_used: bool
    llm_summary: str | None
    llm_issues: list[dict]
    llm_message: str | None
    findings: list[FindingOut]
