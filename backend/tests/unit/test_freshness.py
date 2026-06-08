from app.constructor.freshness import Freshness, compute_state


def test_never_validated_is_sin_validar():
    assert compute_state(current_hash="abc", last_validated_hash=None) == (
        Freshness.sin_validar
    )


def test_matching_hash_is_valido():
    assert compute_state(current_hash="abc", last_validated_hash="abc") == (
        Freshness.valido
    )


def test_differing_hash_is_obsoleto():
    assert compute_state(current_hash="abc", last_validated_hash="xyz") == (
        Freshness.obsoleto
    )
