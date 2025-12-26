from __future__ import annotations

from dataclasses import dataclass
import math

from lps.config import DiurnalConfig
from lps.patterns.base import PatternSchedule


@dataclass(frozen=True, slots=True)
class DiurnalPattern:
    config: DiurnalConfig

    def schedule(self, duration_sec: int) -> PatternSchedule:
        rates: list[float] = []
        for t in range(duration_sec):
            cycle_pos = (t % self.config.cycle_duration_sec) / self.config.cycle_duration_sec
            rates.append(self._shape_rate(cycle_pos))
        return PatternSchedule(rates)

    def _shape_rate(self, cycle_pos: float) -> float:
        min_rps = self.config.min_rps
        max_rps = self.config.max_rps
        if self.config.shape == "gaussian":
            mu = 0.5
            sigma = 0.18
            peak = math.exp(-0.5 * ((cycle_pos - mu) / sigma) ** 2)
        elif self.config.shape == "commuter":
            morning = math.exp(-0.5 * ((cycle_pos - 0.33) / 0.08) ** 2)
            evening = math.exp(-0.5 * ((cycle_pos - 0.72) / 0.1) ** 2)
            peak = (morning + evening) / 2.0
        else:
            peak = (math.sin(2 * math.pi * (cycle_pos - 0.25)) + 1.0) / 2.0
        return min_rps + (max_rps - min_rps) * peak
