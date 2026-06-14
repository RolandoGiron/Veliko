"""Run: .venv/bin/python -m tests.evals.run_citation_evals   (desde backend/)
Golpea Crossref/OpenAlex reales. NO corre en CI."""
import asyncio

import httpx

from app.config import get_settings
from app.verification.lookup import CrossrefOpenAlexClient
from tests.evals.citation_golden import GOLDEN_CITATIONS


async def main() -> None:
    s = get_settings()
    client = CrossrefOpenAlexClient(
        httpx.AsyncClient(), mailto=s.crossref_mailto, timeout_s=s.lookup_timeout_s
    )
    hits = 0
    for surname, year, expected in GOLDEN_CITATIONS:
        r = await client.lookup(surname, year)
        ok = r.status.value == expected
        hits += ok
        print(f"{'✓' if ok else '✗'} {surname} ({year}): {r.status.value} "
              f"(esperado {expected})")
    total = len(GOLDEN_CITATIONS)
    print(f"\n{hits}/{total} correctos ({hits / total:.0%})")


if __name__ == "__main__":
    asyncio.run(main())
