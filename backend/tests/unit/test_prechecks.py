from app.coherence.prechecks import PrecheckCode, run_prechecks
from app.constructor.freshness import Freshness
from app.constructor.node_types import NodeType


def test_empty_content_blocks():
    r = run_prechecks(NodeType.problema, "   ", upstream_states={})
    assert r.ok is False
    assert r.code == PrecheckCode.empty


def test_too_short_blocks():
    r = run_prechecks(NodeType.problema, "tres palabras solas", upstream_states={})
    assert r.ok is False
    assert r.code == PrecheckCode.too_short


def test_unvalidated_upstream_blocks():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(
        NodeType.hipotesis,
        long,
        upstream_states={
            NodeType.problema: Freshness.valido,
            NodeType.objetivos: Freshness.obsoleto,
        },
    )
    assert r.ok is False
    assert r.code == PrecheckCode.upstream_not_valid


def test_passes_when_long_enough_and_upstream_valid():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(
        NodeType.hipotesis,
        long,
        upstream_states={
            NodeType.problema: Freshness.valido,
            NodeType.objetivos: Freshness.valido,
        },
    )
    assert r.ok is True
    assert r.code is None


def test_root_node_passes_without_upstream():
    long = " ".join(["palabra"] * 40)
    r = run_prechecks(NodeType.problema, long, upstream_states={})
    assert r.ok is True
