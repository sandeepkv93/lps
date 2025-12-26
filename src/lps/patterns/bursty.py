from __future__ import annotations

from dataclasses import dataclass
from random import Random

from lps.config import BurstyConfig
from lps.patterns.base import PatternSchedule


@dataclass(frozen=True, slots=True)
class BurstyPattern:
    config: BurstyConfig
    seed: int

    def schedule(self, duration_sec: int) -> PatternSchedule:
        rng = Random(self.seed)
        rates: list[float] = []
        for t in range(duration_sec):
            if self._is_burst(t):
                base = self.config.burst_rps
            else:
                base = self.config.baseline_rps
            jitter = base * self.config.jitter_pct
            rate = max(0.0, rng.uniform(base - jitter, base + jitter))
            rates.append(rate)
        return PatternSchedule(rates)

    def _is_burst(self, t_sec: int) -> bool:
        if self.config.burst_interval_sec <= 0:
            return False
        position = t_sec % self.config.burst_interval_sec
        return position < self.config.burst_duration_sec
