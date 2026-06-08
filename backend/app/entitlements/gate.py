from dataclasses import dataclass

from app.coherence.contracts import CoherenceVerdict
from app.entitlements.tiers import Tier, TIER_CONFIG


@dataclass(frozen=True)
class GateResult:
    mode: str          # "asesor" | "estricto"
    blocked: bool


def apply_gate(verdict: CoherenceVerdict, tier: Tier) -> GateResult:
    cfg = TIER_CONFIG[tier]
    if not cfg.strict:
        return GateResult(mode="asesor", blocked=False)
    return GateResult(mode="estricto", blocked=verdict.score < cfg.strict_threshold)
