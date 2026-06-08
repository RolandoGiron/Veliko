from app.constructor.node_types import NodeType
from app.i18n.prompts import SYSTEM_PROMPT_ES, build_user_prompt


def test_system_prompt_mentions_rubric_dimensions():
    for dim in ("coherencia", "falsabilidad", "claridad", "alineacion_objetivos", "medibilidad"):
        assert dim in SYSTEM_PROMPT_ES


def test_user_prompt_includes_content_and_upstream():
    prompt = build_user_prompt(
        node_type=NodeType.hipotesis,
        content="Mi hipotesis.",
        upstream={NodeType.problema: "El problema.", NodeType.objetivos: "Los objetivos."},
    )
    assert "hipotesis" in prompt
    assert "Mi hipotesis." in prompt
    assert "El problema." in prompt
    assert "Los objetivos." in prompt


def test_user_prompt_for_root_has_no_upstream_section():
    prompt = build_user_prompt(node_type=NodeType.problema, content="P", upstream={})
    assert "P" in prompt
