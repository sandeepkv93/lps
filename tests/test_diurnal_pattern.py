from __future__ import annotations

from dataclasses import asdict

from hypothesis import given, strategies as st

from lps.config import DiurnalConfig, PatternConfig, PatternType
from lps.patterns import schedule_for


@given(
    min_rps=st.floats(min_value=1.0, max_value=50.0),
    max_rps=st.floats(min_value=60.0, max_value=500.0),
    cycle=st.integers(min_value=60, max_value=600),
)
def test_diurnal_bounds(min_rps: float, max_rps: float, cycle: int) -> None:
    cfg = DiurnalConfig(min_rps=min_rps, max_rps=max_rps, cycle_duration_sec=cycle, shape="sine")
    pattern = PatternConfig(PatternType.DIURNAL, asdict(cfg))
    schedule = schedule_for(pattern, duration_sec=cycle, seed=1)
    for rate in schedule.rates_per_sec:
        assert min_rps <= rate <= max_rps
