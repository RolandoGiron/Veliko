from enum import StrEnum


class NodeType(StrEnum):
    problema = "problema"
    objetivos = "objetivos"
    hipotesis = "hipotesis"
    variables = "variables"
    metodologia = "metodologia"
    instrumentos = "instrumentos"


DEPENDENCY_CHAIN: list[NodeType] = [
    NodeType.problema,
    NodeType.objetivos,
    NodeType.hipotesis,
    NodeType.variables,
    NodeType.metodologia,
    NodeType.instrumentos,
]

# Minimum word count per node type for the deterministic pre-check (spec §11 default).
MIN_WORDS: dict[NodeType, int] = {
    NodeType.problema: 30,
    NodeType.objetivos: 15,
    NodeType.hipotesis: 10,
    NodeType.variables: 10,
    NodeType.metodologia: 30,
    NodeType.instrumentos: 15,
}


def upstream_types(node_type: NodeType) -> list[NodeType]:
    """All node types preceding `node_type` in the dependency chain, in order."""
    idx = DEPENDENCY_CHAIN.index(node_type)
    return DEPENDENCY_CHAIN[:idx]
