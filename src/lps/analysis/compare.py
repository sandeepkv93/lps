from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True, slots=True)
class Regression:
    metric: str
    delta_pct: float
    message: str


def compare_runs(base: pd.DataFrame, candidate: pd.DataFrame) -> list[Regression]:
    regressions: list[Regression] = []
    if base.empty or candidate.empty:
        return regressions
    merged = base.merge(candidate, on="second", suffixes=("_base", "_cand"))
    if merged.empty:
        return regressions
    base_p99 = merged["p99_ms_base"].mean()
    cand_p99 = merged["p99_ms_cand"].mean()
    if base_p99 > 0:
        delta = (cand_p99 - base_p99) / base_p99
        if delta > 0.2:
            regressions.append(
                Regression(
                    metric="p99_ms",
                    delta_pct=delta * 100,
                    message="p99 latency increased materially",
                )
            )
    base_err = merged["error_rate_base"].mean()
    cand_err = merged["error_rate_cand"].mean()
    if base_err > 0:
        delta = (cand_err - base_err) / base_err
        if delta > 0.3:
            regressions.append(
                Regression(
                    metric="error_rate",
                    delta_pct=delta * 100,
                    message="error rate regression detected",
                )
            )
    base_rps = merged["achieved_rps_base"].mean()
    cand_rps = merged["achieved_rps_cand"].mean()
    if base_rps > 0:
        delta = (base_rps - cand_rps) / base_rps
        if delta > 0.2:
            regressions.append(
                Regression(
                    metric="achieved_rps",
                    delta_pct=delta * 100,
                    message="throughput regression detected",
                )
            )
    return regressions
