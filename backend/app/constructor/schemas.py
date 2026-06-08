from pydantic import BaseModel


class ProjectIn(BaseModel):
    title: str
    language: str = "es"


class NodeOut(BaseModel):
    type: str
    content: str
    state: str  # Freshness value


class ProjectSummary(BaseModel):
    id: str
    title: str
    language: str


class ProjectDetail(ProjectSummary):
    nodes: list[NodeOut]


class NodeIn(BaseModel):
    content: str
