import pytest
from pydantic import ValidationError

from app.constructor.node_types import NodeType
from app.i18n.prompts import CITATION_SYSTEM_PROMPT_ES, build_citation_prompt
from app.verification.contracts import CitationStyleReview, StyleIssue


def test_valid_review():
    r = CitationStyleReview(
        issues=[StyleIssue(severity="menor", code="orden_cronologico",
                           message="Ordena las citas múltiples por año.",
                           citation="(López, 2020; García, 2019)")],
        summary="Estilo APA correcto en general.",
    )
    assert r.issues[0].severity == "menor"


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        StyleIssue(severity="grave", code="x", message="y", citation=None)


def test_system_prompt_is_spanish_and_forbids_rewriting():
    assert "español" in CITATION_SYSTEM_PROMPT_ES
    assert "NUNCA" in CITATION_SYSTEM_PROMPT_ES


def test_build_citation_prompt_includes_nodes_and_citations():
    p = build_citation_prompt(
        {NodeType.problema: "Texto con (García, 2020)."},
        ["(García, 2020)"],
    )
    assert "(García, 2020)" in p
    assert "Problema" in p
