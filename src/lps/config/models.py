from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class LoadModel(str, Enum):
    OPEN_LOOP = "open_loop"
    CLOSED_LOOP = "closed_loop"


class PatternType(str, Enum):
    BURSTY = "bursty"
    DIURNAL = "diurnal"
    VIRAL = "viral_spike"


@dataclass(frozen=True, slots=True)
class TargetConfig:
    base_url: str
    method: str = "GET"
    timeout_sec: float = 10.0
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    enabled: bool = False
    max_retries: int = 2
    base_delay_sec: float = 0.2
    max_delay_sec: float = 2.0


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    enabled: bool = False
    window_size: int = 20
    error_rate_threshold: float = 0.5
    open_cooldown_sec: float = 5.0


@dataclass(frozen=True, slots=True)
class BurstyConfig:
    baseline_rps: float
    burst_rps: float
    burst_duration_sec: int
    burst_interval_sec: int
    jitter_pct: float = 0.05


@dataclass(frozen=True, slots=True)
class DiurnalConfig:
    min_rps: float
    max_rps: float
    cycle_duration_sec: int
    shape: str = "sine"  # sine | gaussian | commuter


@dataclass(frozen=True, slots=True)
class ViralSpikeConfig:
    baseline_rps: float
    spike_multiplier: float
    ramp_up_sec: int
    peak_hold_sec: int
    decay_half_life_sec: int


@dataclass(frozen=True, slots=True)
class PatternConfig:
    pattern_type: PatternType
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RunConfig:
    target: TargetConfig
    pattern: PatternConfig
    duration_sec: int
    load_model: LoadModel = LoadModel.OPEN_LOOP
    closed_loop_workers: int = 50
    seed: int = 7
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    run_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    def to_metadata(self) -> Mapping[str, Any]:
        return {
            "run_id": self.run_id or "",
            "created_at": self.created_at.isoformat(),
            "duration_sec": self.duration_sec,
            "load_model": self.load_model.value,
            "closed_loop_workers": self.closed_loop_workers,
            "seed": self.seed,
            "notes": self.notes,
            "pattern": {
                "type": self.pattern.pattern_type.value,
                "params": dict(self.pattern.params),
            },
            "target": {
                "base_url": self.target.base_url,
                "method": self.target.method,
                "timeout_sec": self.target.timeout_sec,
                "headers": dict(self.target.headers),
            },
            "retry": {
                "enabled": self.retry.enabled,
                "max_retries": self.retry.max_retries,
                "base_delay_sec": self.retry.base_delay_sec,
                "max_delay_sec": self.retry.max_delay_sec,
            },
            "circuit_breaker": {
                "enabled": self.circuit_breaker.enabled,
                "window_size": self.circuit_breaker.window_size,
                "error_rate_threshold": self.circuit_breaker.error_rate_threshold,
                "open_cooldown_sec": self.circuit_breaker.open_cooldown_sec,
            },
        }
