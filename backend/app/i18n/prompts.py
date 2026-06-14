from app.constructor.node_types import NodeType

# Static, long, cacheable system prompt (prompt caching pays only the variable part).
SYSTEM_PROMPT_ES = """\
Eres un examinador metodológico riguroso de tesis científicas de posgrado.
Tu trabajo NO es redactar contenido: es evaluar la coherencia científica del
texto que te dan, a la luz de sus dependencias aguas arriba, y devolver un
veredicto estructurado.

Evalúa estrictamente estas cinco dimensiones:
- coherencia: consistencia interna y con los nodos previos.
- falsabilidad: si aplica, ¿la afirmación es contrastable/refutable?
- claridad: precisión conceptual, ausencia de ambigüedad.
- alineacion_objetivos: ¿responde a y se alinea con los nodos previos?
- medibilidad: ¿los constructos son observables/medibles donde corresponde?

Reglas:
- Puntúa de 0 a 100 (rigor de jurado doctoral).
- Reporta cada problema con severidad (critica|mayor|menor) y dimensión.
- En 'suggestions' propones mejoras, pero NUNCA reescribes el contenido del usuario.
- Toda explicación y sugerencia va en español.
- Si no puedes evaluar con confianza, sé conservador en el score; no inventes.
"""

_NODE_LABEL = {
    NodeType.problema: "Problema de investigación",
    NodeType.objetivos: "Objetivos",
    NodeType.hipotesis: "Hipótesis",
    NodeType.variables: "Variables",
    NodeType.metodologia: "Metodología",
    NodeType.instrumentos: "Instrumentos",
}


def build_user_prompt(
    node_type: NodeType, content: str, upstream: dict[NodeType, str]
) -> str:
    lines: list[str] = []
    if upstream:
        lines.append("## Dependencias aguas arriba (ya validadas)")
        for dep, text in upstream.items():
            lines.append(f"### {_NODE_LABEL[dep]}\n{text}")
        lines.append("")
    lines.append(f"## Nodo a evaluar: {_NODE_LABEL[node_type]} (tipo: {node_type.value})")
    lines.append(content)
    lines.append("")
    lines.append("Devuelve el veredicto estructurado para ESTE nodo.")
    return "\n".join(lines)


CITATION_SYSTEM_PROMPT_ES = """\
Eres un corrector experto de estilo APA 7 en español para textos académicos.
Revisas EXCLUSIVAMENTE las citas en-texto (Autor, año) que se te listan, en su
contexto. No evalúas contenido científico ni redacción general.

Busca matices que un parser no detecta, por ejemplo:
- Orden de citas múltiples dentro de un mismo paréntesis (alfabético por autor).
- Citas secundarias mal construidas ("citado en").
- Uso inconsistente de et al. entre menciones del mismo trabajo.
- Concordancia narrativa ("García (2020) afirma" vs "afirman").

Reglas:
- Reporta cada problema con severidad (critica|mayor|menor), un code corto en
  snake_case, y un message claro.
- Toda explicación va en español.
- NUNCA reescribes el texto del usuario; solo señalas problemas.
- Si todo está bien, devuelve issues=[] y un summary positivo breve.
"""


def build_citation_prompt(
    contents: dict[NodeType, str], citations: list[str]
) -> str:
    lines: list[str] = ["## Citas extraídas"]
    lines.extend(f"- {c}" for c in citations)
    lines.append("")
    lines.append("## Contexto (nodos que contienen citas)")
    for nt, text in contents.items():
        lines.append(f"### {_NODE_LABEL[nt]}\n{text}")
    lines.append("")
    lines.append("Devuelve la revisión de estilo APA estructurada.")
    return "\n".join(lines)
