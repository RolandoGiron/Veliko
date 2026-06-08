from app.constructor.node_types import (
    DEPENDENCY_CHAIN,
    NodeType,
    upstream_types,
)


def test_chain_order():
    assert DEPENDENCY_CHAIN == [
        NodeType.problema,
        NodeType.objetivos,
        NodeType.hipotesis,
        NodeType.variables,
        NodeType.metodologia,
        NodeType.instrumentos,
    ]


def test_upstream_of_root_is_empty():
    assert upstream_types(NodeType.problema) == []


def test_upstream_is_all_preceding_in_order():
    assert upstream_types(NodeType.hipotesis) == [
        NodeType.problema,
        NodeType.objetivos,
    ]
    assert upstream_types(NodeType.instrumentos) == [
        NodeType.problema,
        NodeType.objetivos,
        NodeType.hipotesis,
        NodeType.variables,
        NodeType.metodologia,
    ]
