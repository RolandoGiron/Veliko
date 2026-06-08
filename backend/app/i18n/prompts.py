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
