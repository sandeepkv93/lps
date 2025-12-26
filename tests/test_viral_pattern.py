from __future__ import annotations

from dataclasses import asdict

from lps.config import PatternConfig, PatternType, ViralSpikeConfig
from lps.patterns import schedule_for


def test_viral_ramp_and_decay() -> None:
    cfg = ViralSpikeConfig(
        baseline_rps=10.0,
        spike_multiplier=5.0,
        ramp_up_sec=4,
        peak_hold_sec=3,
        decay_half_life_sec=2,
    )
    pattern = PatternConfig(PatternType.VIRAL, asdict(cfg))
    schedule = schedule_for(pattern, duration_sec=15, seed=1).rates_per_sec
    ramp = schedule[:4]
    assert ramp == sorted(ramp)
    hold = schedule[4:7]
    assert all(rate == hold[0] for rate in hold)
    decay = schedule[7:]
    assert decay == sorted(decay, reverse=True)
