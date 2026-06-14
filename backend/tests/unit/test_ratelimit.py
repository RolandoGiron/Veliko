import pytest

from app.entitlements.errors import RateLimited
from app.entitlements.ratelimit import SlidingWindowLimiter


def test_allows_up_to_max():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)


def test_blocks_over_max_within_window():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)
    with pytest.raises(RateLimited):
        lim.check("p1", now=3.0)


def test_window_slides():
    lim = SlidingWindowLimiter(max_events=3, window_s=60)
    for t in (0.0, 1.0, 2.0):
        lim.check("p1", now=t)
    lim.check("p1", now=61.0)  # first event expired


def test_keys_are_independent():
    lim = SlidingWindowLimiter(max_events=1, window_s=60)
    lim.check("p1", now=0.0)
    lim.check("p2", now=0.0)
