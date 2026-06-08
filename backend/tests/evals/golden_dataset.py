from dataclasses import dataclass

from app.constructor.node_types import NodeType


@dataclass(frozen=True)
class EvalCase:
    name: str
    node_type: NodeType
    content: str
    upstream: dict[NodeType, str]
    expected_score_min: int
    expected_score_max: int
    expected_dimension: str | None  # a dimension that SHOULD appear in issues, or None


_PROBLEMA_OK = (
    "Existe un vacío sobre cómo la carga cognitiva afecta la retención en "
    "estudiantes de posgrado en entornos de aprendizaje en línea sincrónico, "
    "lo que limita el diseño de intervenciones efectivas."
)
_OBJETIVOS_OK = (
    "Determinar el efecto de la carga cognitiva sobre la retención de contenidos "
    "en estudiantes de posgrado en entornos sincrónicos en línea."
)

CASES: list[EvalCase] = [
    EvalCase(
        name="problema_solido",
        node_type=NodeType.problema,
        content=_PROBLEMA_OK,
        upstream={},
        expected_score_min=70, expected_score_max=100, expected_dimension=None,
    ),
    EvalCase(
        name="problema_vago",
        node_type=NodeType.problema,
        content=(
            "Queremos estudiar la educación en línea porque es un tema interesante "
            "y actual que a mucha gente le importa hoy en día en el mundo entero."
        ),
        upstream={},
        expected_score_min=0, expected_score_max=55, expected_dimension="claridad",
    ),
    EvalCase(
        name="hipotesis_no_falsable",
        node_type=NodeType.hipotesis,
        content="La educación es importante para el éxito de las personas.",
        upstream={NodeType.problema: _PROBLEMA_OK, NodeType.objetivos: _OBJETIVOS_OK},
        expected_score_min=0, expected_score_max=50, expected_dimension="falsabilidad",
    ),
    EvalCase(
        name="hipotesis_falsable",
        node_type=NodeType.hipotesis,
        content=(
            "A mayor carga cognitiva extrínseca durante una sesión sincrónica, "
            "menor será la retención de contenidos medida a las 48 horas."
        ),
        upstream={NodeType.problema: _PROBLEMA_OK, NodeType.objetivos: _OBJETIVOS_OK},
        expected_score_min=70, expected_score_max=100, expected_dimension=None,
    ),
    EvalCase(
        name="objetivos_desalineados",
        node_type=NodeType.objetivos,
        content="Diseñar una aplicación móvil para vender cursos en línea.",
        upstream={NodeType.problema: _PROBLEMA_OK},
        expected_score_min=0, expected_score_max=50, expected_dimension="alineacion_objetivos",
    ),
    EvalCase(
        name="variables_no_medibles",
        node_type=NodeType.variables,
        content="La felicidad del estudiante y la calidad general del aprendizaje.",
        upstream={
            NodeType.problema: _PROBLEMA_OK,
            NodeType.objetivos: _OBJETIVOS_OK,
            NodeType.hipotesis: (
                "A mayor carga cognitiva extrínseca, menor retención a las 48 horas."
            ),
        },
        expected_score_min=0, expected_score_max=55, expected_dimension="medibilidad",
    ),
]
