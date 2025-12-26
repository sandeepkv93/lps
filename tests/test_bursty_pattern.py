from __future__ import annotations

from dataclasses import asdict

from lps.config import BurstyConfig, PatternConfig, PatternType
from lps.patterns import schedule_for


def test_bursty_pattern_intervals() -> None:
    cfg = BurstyConfig(
        baseline_rps=10.0,
        burst_rps=100.0,
        burst_duration_sec=3,
        burst_interval_sec=10,
        jitter_pct=0.0,
    )
    pattern = PatternConfig(PatternType.BURSTY, asdict(cfg))
    schedule = schedule_for(pattern, duration_sec=20, seed=1)
    assert schedule.duration_sec() == 20
    for t in range(20):
        rate = schedule.rate_at(t)
        if t % 10 < 3:
            assert rate == 100.0
        else:
            assert rate == 10.0
