from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

from lps.metrics.models import ErrorType, PerSecondMetrics, RequestEvent


def aggregate_per_second(
    run_id: str,
    events: Iterable[RequestEvent],
    requested_rates: list[float],
    start_mono: float,
) -> list[PerSecondMetrics]:
    buckets: dict[int, list[RequestEvent]] = defaultdict(list)
    for event in events:
        second = max(0, int(event.mono_time - start_mono))
        buckets[second].append(event)

    metrics: list[PerSecondMetrics] = []
    duration = len(requested_rates)
    for second in range(duration):
        bucket = buckets.get(second, [])
        latencies = [e.latency_ms for e in bucket if e.latency_ms >= 0]
        achieved = len(bucket)
        error_count = sum(1 for e in bucket if e.error_type is not None)
        timeout_count = sum(1 for e in bucket if e.error_type is ErrorType.TIMEOUT)
        if latencies:
            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))
        else:
            p50 = p95 = p99 = 0.0
        total = max(1, achieved)
        metrics.append(
            PerSecondMetrics(
                run_id=run_id,
                second=second,
                requested_rps=requested_rates[second],
                achieved_rps=float(achieved),
                p50_ms=p50,
                p95_ms=p95,
                p99_ms=p99,
                error_rate=error_count / total,
                timeout_rate=timeout_count / total,
            )
        )
    return metrics
