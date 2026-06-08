from dataclasses import dataclass
from enum import StrEnum


class Tier(StrEnum):
    free = "free"
    pro = "pro"
    doctoral = "doctoral"
    university = "university"


@dataclass(frozen=True)
class TierConfig:
    monthly_quota: int
    anthropic_model: str
    openai_model: str
    strict: bool
    strict_threshold: int  # block if score < threshold (strict only)


_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"
_GPT_MINI = "gpt-4o-mini"
_GPT = "gpt-4o"

TIER_CONFIG: dict[Tier, TierConfig] = {
    Tier.free: TierConfig(20, _HAIKU, _GPT_MINI, strict=False, strict_threshold=70),
    Tier.pro: TierConfig(200, _HAIKU, _GPT_MINI, strict=False, strict_threshold=70),
    Tier.doctoral: TierConfig(1000, _SONNET, _GPT, strict=True, strict_threshold=70),
    Tier.university: TierConfig(5000, _SONNET, _GPT, strict=False, strict_threshold=70),
}
