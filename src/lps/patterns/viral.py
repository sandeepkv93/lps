from __future__ import annotations

from dataclasses import dataclass
import math

from lps.config import ViralSpikeConfig
from lps.patterns.base import PatternSchedule


@dataclass(frozen=True, slots=True)
class ViralSpikePattern:
    config: ViralSpikeConfig

    def schedule(self, duration_sec: int) -> PatternSchedule:
        rates: list[float] = []
        for t in range(duration_sec):
            rates.append(self._rate_at(t))
        return PatternSchedule(rates)

    def _rate_at(self, t_sec: int) -> float:
        base = self.config.baseline_rps
        peak = base * self.config.spike_multiplier
        ramp_end = self.config.ramp_up_sec
        hold_end = ramp_end + self.config.peak_hold_sec
        if t_sec < ramp_end and ramp_end > 0:
            return base + (peak - base) * (t_sec / ramp_end)
        if t_sec < hold_end:
            return peak
        elapsed = t_sec - hold_end
        half_life = max(1, self.config.decay_half_life_sec)
        decay = math.exp(-math.log(2) * elapsed / half_life)
        return base + (peak - base) * decay
