from __future__ import annotations

from typing import Any, Mapping

from lps.config import BurstyConfig, DiurnalConfig, PatternConfig, PatternType, ViralSpikeConfig
from lps.patterns.base import PatternSchedule
from lps.patterns.bursty import BurstyPattern
from lps.patterns.diurnal import DiurnalPattern
from lps.patterns.viral import ViralSpikePattern


def schedule_for(pattern: PatternConfig, duration_sec: int, seed: int) -> PatternSchedule:
    if pattern.pattern_type is PatternType.BURSTY:
        cfg = _coerce(BurstyConfig, pattern.params)
        return BurstyPattern(cfg, seed=seed).schedule(duration_sec)
    if pattern.pattern_type is PatternType.DIURNAL:
        cfg = _coerce(DiurnalConfig, pattern.params)
        return DiurnalPattern(cfg).schedule(duration_sec)
    if pattern.pattern_type is PatternType.VIRAL:
        cfg = _coerce(ViralSpikeConfig, pattern.params)
        return ViralSpikePattern(cfg).schedule(duration_sec)
    msg = f"Unsupported pattern type: {pattern.pattern_type}"
    raise ValueError(msg)


def _coerce(cls: type[Any], params: Mapping[str, Any]) -> Any:
    return cls(**params)
