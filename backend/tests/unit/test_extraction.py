from app.constructor.node_types import NodeType
from app.verification.extraction import extract_citations


def _ext(text: str):
    return extract_citations(NodeType.problema, text)


def test_narrative_single_author():
    [c] = _ext("Como demostró García (2020), el problema persiste.")
    assert (c.surname, c.year, c.narrative) == ("García", "2020", True)
    assert c.surnames == ("García",)
    assert c.et_al is False


def test_parenthetical_single_author():
    [c] = _ext("El problema persiste (García, 2020).")
    assert (c.surname, c.year, c.narrative) == ("García", "2020", False)
    assert c.raw == "(García, 2020)"


def test_parenthetical_two_authors_ampersand():
    [c] = _ext("Esto se confirmó (García & López, 2019).")
    assert c.surnames == ("García", "López")


def test_narrative_two_authors_y():
    [c] = _ext("García y López (2019) confirmaron esto.")
    assert c.surnames == ("García", "López")
    assert c.narrative is True


def test_et_al():
    [c] = _ext("Según García et al. (2021), es así.")
    assert c.et_al is True
    assert c.surname == "García"


def test_multiple_citations_in_one_paren():
    cs = _ext("Varios lo afirman (García, 2019; López, 2020).")
    assert [(c.surname, c.year) for c in cs] == [("García", "2019"), ("López", "2020")]


def test_with_page_number():
    [c] = _ext("Se definió así (García et al., 2021, p. 23).")
    assert (c.surname, c.year) == ("García", "2021")


def test_year_suffix_and_sf():
    cs = _ext("Primero (García, 2020a) y luego (López, s.f.).")
    assert [c.year for c in cs] == ["2020a", "s.f."]


def test_missing_comma_detected():
    [c] = _ext("Mal citado (García 2020).")
    assert c.missing_comma is True
    assert (c.surname, c.year) == ("García", "2020")


def test_plain_parentheses_ignored():
    assert _ext("El acrónimo (OMS) y el dato (45%) no son citas.") == []


def test_ordered_by_position():
    cs = _ext("López (2018) lo dijo antes (García, 2020).")
    assert [c.surname for c in cs] == ["López", "García"]


def test_narrative_with_page_number():
    [c] = _ext("García (2020, p. 45) señala que el problema es complejo.")
    assert (c.surname, c.year, c.narrative) == ("García", "2020", True)
