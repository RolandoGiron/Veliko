from dataclasses import dataclass
from enum import StrEnum

from app.constructor.freshness import Freshness
from app.constructor.node_types import MIN_WORDS, NodeType, upstream_types


class PrecheckCode(StrEnum):
    empty = "empty"
    too_short = "too_short"
    upstream_not_valid = "upstream_not_valid"


@dataclass(frozen=True)
class PrecheckResult:
    ok: bool
    code: PrecheckCode | None = None
    message: str | None = None


def run_prechecks(
    node_type: NodeType,
    content: str,
    upstream_states: dict[NodeType, Freshness],
) -> PrecheckResult:
    stripped = content.strip()
    if not stripped:
        return PrecheckResult(False, PrecheckCode.empty, "El nodo está vacío.")

    if len(stripped.split()) < MIN_WORDS[node_type]:
        return PrecheckResult(
            False,
            PrecheckCode.too_short,
            f"Necesita al menos {MIN_WORDS[node_type]} palabras para validar.",
        )

    for dep in upstream_types(node_type):
        if upstream_states.get(dep) != Freshness.valido:
            return PrecheckResult(
                False,
                PrecheckCode.upstream_not_valid,
                f"Primero valida '{dep.value}': de él depende este nodo.",
            )

    return PrecheckResult(True)
