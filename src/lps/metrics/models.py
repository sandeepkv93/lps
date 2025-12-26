from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorType(str, Enum):
    TIMEOUT = "timeout"
    CONNECT = "connect"
    READ = "read"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class RequestEvent:
    run_id: str
    wall_time: float
    mono_time: float
    latency_ms: float
    status_code: int | None
    error_type: ErrorType | None
    bytes_sent: int
    bytes_received: int


@dataclass(frozen=True, slots=True)
class PerSecondMetrics:
    run_id: str
    second: int
    requested_rps: float
    achieved_rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_rate: float
    timeout_rate: float
