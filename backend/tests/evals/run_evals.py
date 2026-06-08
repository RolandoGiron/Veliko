"""Run with: python -m tests.evals.run_evals  (requires real API keys; costs money)."""
from datetime import date

from app.coherence.service import _singleton_gateway
from app.i18n.prompts import SYSTEM_PROMPT_ES, build_user_prompt
from tests.evals.golden_dataset import CASES


def main() -> None:
    gw = _singleton_gateway()
    passed = 0
    for c in CASES:
        res = gw.validate(
            model="claude-haiku-4-5-20251001",
            system_prompt=SYSTEM_PROMPT_ES,
            user_prompt=build_user_prompt(c.node_type, c.content, c.upstream),
            today=date.today(),
        )
        v = res.verdict
        score_ok = c.expected_score_min <= v.score <= c.expected_score_max
        dim_ok = c.expected_dimension is None or any(
            i.dimension == c.expected_dimension for i in v.issues
        )
        ok = score_ok and dim_ok
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {c.name}: score={v.score} dims={[i.dimension for i in v.issues]}")
    print(f"\n{passed}/{len(CASES)} eval cases passed")


if __name__ == "__main__":
    main()
