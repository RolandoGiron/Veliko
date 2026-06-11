import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CitationRun(Base):
    __tablename__ = "citation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("research_projects.id"), index=True
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    project_issues: Mapped[list] = mapped_column(JSON, default=list)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_issues: Mapped[list] = mapped_column(JSON, default=list)
    llm_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )


class CitationFinding(Base):
    __tablename__ = "citation_findings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("citation_runs.id"), index=True)
    node_type: Mapped[str] = mapped_column(String, nullable=False)
    raw: Mapped[str] = mapped_column(String, nullable=False)
    surname: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[str] = mapped_column(String, nullable=False)
    narrative: Mapped[bool] = mapped_column(Boolean, default=False)
    format_issues: Mapped[list] = mapped_column(JSON, default=list)
    existence_status: Mapped[str] = mapped_column(String, nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list)


class CitationLookup(Base):
    __tablename__ = "citation_lookups"

    surname_norm: Mapped[str] = mapped_column(String, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
