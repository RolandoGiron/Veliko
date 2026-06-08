import hashlib

from app.constructor.node_types import NodeType, upstream_types


def compute_node_hash(node_type: NodeType, contents: dict[NodeType, str]) -> str:
    """sha256 over upstream contents (in chain order) + own content.

    `contents` maps node type -> current content. Missing entries count as "".
    """
    parts: list[str] = []
    for dep in upstream_types(node_type):
        parts.append(f"{dep.value}:{contents.get(dep, '')}")
    parts.append(f"{node_type.value}:{contents.get(node_type, '')}")
    joined = "\x1e".join(parts)  # record separator, unlikely in content
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
