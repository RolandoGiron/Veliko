from app.coherence.contracts import CoherenceVerdict
from app.entitlements.gate import apply_gate
from app.entitlements.tiers import Tier, TIER_CONFIG


def _verdict(score: int) -> CoherenceVerdict:
    return CoherenceVerdict(score=score, issues=[], suggestions=[], summary="s")


def test_advisor_never_blocks_even_low_score():
    g = apply_gate(_verdict(10), Tier.free)
    assert g.blocked is False
    assert g.mode == "asesor"


def test_doctoral_strict_blocks_below_threshold():
    g = apply_gate(_verdict(50), Tier.doctoral)
    assert g.mode == "estricto"
    assert g.blocked is True


def test_doctoral_strict_allows_at_or_above_threshold():
    g = apply_gate(_verdict(70), Tier.doctoral)
    assert g.blocked is False


def test_every_tier_has_models_and_quota():
    for tier in Tier:
        cfg = TIER_CONFIG[tier]
        assert cfg.monthly_quota > 0
        assert cfg.anthropic_model
        assert cfg.openai_model
