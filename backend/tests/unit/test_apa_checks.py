from datetime import date

from app.constructor.node_types import NodeType
from app.verification.apa_checks import run_apa_checks
from app.verification.extraction import extract_citations

TODAY = date(2026, 6, 11)


def _issues(text: str):
    return run_apa_checks(extract_citations(NodeType.problema, text), TODAY)


def test_no_citations_informative():
    [i] = run_apa_checks([], TODAY)
    assert (i.code, i.severity) == ("sin_citas", "menor")


def test_clean_citation_no_issues():
    assert _issues("Lo dijo (García, 2020).") == []


def test_missing_comma_flagged_mayor():
    issues = _issues("Mal (García 2020).")
    assert [(i.code, i.severity) for i in issues] == [("falta_coma", "mayor")]


def test_ampersand_in_narrative_flagged():
    issues = _issues("García & López (2019) lo dijeron.")
    assert any(i.code == "ampersand_en_narrativa" and i.severity == "menor" for i in issues)


def test_y_in_parenthetical_flagged():
    issues = _issues("Lo dijeron (García y López, 2019).")
    assert any(i.code == "y_en_parentetica" and i.severity == "menor" for i in issues)


def test_three_plus_authors_listed_flagged():
    issues = _issues("Lo dijeron (García, López & Pérez, 2019).")
    assert any(i.code == "demasiados_autores" and i.severity == "mayor" for i in issues)


def test_et_al_not_flagged_as_too_many():
    assert _issues("Lo dijeron (García et al., 2019).") == []


def test_future_year_flagged():
    issues = _issues("Se publicará (García, 2030).")
    assert any(i.code == "anio_futuro" and i.severity == "mayor" for i in issues)


def test_next_year_tolerated():
    assert _issues("En prensa (García, 2027).") == []
