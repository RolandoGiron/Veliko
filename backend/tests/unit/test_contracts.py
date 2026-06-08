import pytest
from pydantic import ValidationError

from app.coherence.contracts import CoherenceVerdict, Issue


def test_valid_verdict():
    v = CoherenceVerdict(
        score=80,
        issues=[
            Issue(
                severity="mayor",
                dimension="falsabilidad",
                explanation="La hipotesis no es falsable.",
                location=None,
            )
        ],
        suggestions=["Reformular como prediccion contrastable."],
        summary="Coherente pero con una hipotesis debil.",
    )
    assert v.score == 80
    assert v.issues[0].dimension == "falsabilidad"


def test_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        CoherenceVerdict(score=120, issues=[], suggestions=[], summary="x")


def test_invalid_dimension_rejected():
    with pytest.raises(ValidationError):
        Issue(severity="mayor", dimension="inventada", explanation="x", location=None)
