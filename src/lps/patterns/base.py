from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TrafficPattern(Protocol):
    def rate_at(self, t_sec: float) -> float:
        ...


@dataclass(frozen=True, slots=True)
class PatternSchedule:
    rates_per_sec: list[float]

    def duration_sec(self) -> int:
        return len(self.rates_per_sec)

    def rate_at(self, t_sec: float) -> float:
        idx = int(t_sec)
        if idx < 0 or idx >= len(self.rates_per_sec):
            return 0.0
        return self.rates_per_sec[idx]
