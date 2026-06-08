from app.constructor.hashing import compute_node_hash
from app.constructor.node_types import NodeType


def test_hash_is_deterministic():
    contents = {NodeType.problema: "el problema", NodeType.objetivos: "los objetivos"}
    h1 = compute_node_hash(NodeType.objetivos, contents)
    h2 = compute_node_hash(NodeType.objetivos, contents)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_hash_changes_when_own_content_changes():
    base = {NodeType.problema: "P", NodeType.objetivos: "O1"}
    changed = {NodeType.problema: "P", NodeType.objetivos: "O2"}
    assert compute_node_hash(NodeType.objetivos, base) != compute_node_hash(
        NodeType.objetivos, changed
    )


def test_hash_changes_when_upstream_changes():
    base = {NodeType.problema: "P1", NodeType.objetivos: "O"}
    changed = {NodeType.problema: "P2", NodeType.objetivos: "O"}
    # editing the upstream `problema` must invalidate downstream `objetivos`
    assert compute_node_hash(NodeType.objetivos, base) != compute_node_hash(
        NodeType.objetivos, changed
    )


def test_root_hash_ignores_other_nodes():
    a = {NodeType.problema: "P", NodeType.objetivos: "O1"}
    b = {NodeType.problema: "P", NodeType.objetivos: "O2"}
    # problema has no upstream; downstream edits must NOT change its hash
    assert compute_node_hash(NodeType.problema, a) == compute_node_hash(
        NodeType.problema, b
    )


def test_missing_upstream_content_treated_as_empty():
    contents = {NodeType.objetivos: "O"}  # problema absent
    # must not raise; absent upstream contributes empty string
    assert len(compute_node_hash(NodeType.objetivos, contents)) == 64
