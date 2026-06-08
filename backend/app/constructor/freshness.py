from enum import StrEnum


class Freshness(StrEnum):
    sin_validar = "sin_validar"   # ⚪
    valido = "valido"             # 🟢
    obsoleto = "obsoleto"         # 🟡


def compute_state(current_hash: str, last_validated_hash: str | None) -> Freshness:
    if last_validated_hash is None:
        return Freshness.sin_validar
    if current_hash == last_validated_hash:
        return Freshness.valido
    return Freshness.obsoleto
