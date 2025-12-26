from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True, slots=True)
class SignalWindow:
    start_sec: int
    end_sec: int
    label: str


def queueing_indicator(per_second: pd.DataFrame) -> list[SignalWindow]:
    windows: list[SignalWindow] = []
    if per_second.empty:
        return windows
    rising = (per_second["p99_ms"].diff() > 0) & (per_second["achieved_rps"].diff().abs() < 1)
    for idx in per_second.index[rising.fillna(False)]:
        second = int(per_second.loc[idx, "second"])
        windows.append(SignalWindow(second, second + 1, "queueing"))
    return windows


def overload_indicator(per_second: pd.DataFrame) -> list[SignalWindow]:
    windows: list[SignalWindow] = []
    if per_second.empty:
        return windows
    falling = per_second["achieved_rps"].diff() < 0
    errors = per_second["error_rate"].diff() > 0
    for idx in per_second.index[(falling & errors).fillna(False)]:
        second = int(per_second.loc[idx, "second"])
        windows.append(SignalWindow(second, second + 1, "overload"))
    return windows


def autoscaling_lag(per_second: pd.DataFrame) -> list[SignalWindow]:
    windows: list[SignalWindow] = []
    if per_second.empty:
        return windows
    demand_spike = per_second["requested_rps"].diff() > 0
    throughput_catch = per_second["achieved_rps"] >= per_second["requested_rps"] * 0.9
    spike_idx = per_second.index[demand_spike.fillna(False)]
    if spike_idx.empty:
        return windows
    spike_second = int(per_second.loc[spike_idx[0], "second"])
    catch_idx = per_second.index[throughput_catch & (per_second["second"] >= spike_second)]
    if catch_idx.empty:
        return windows
    catch_second = int(per_second.loc[catch_idx[0], "second"])
    if catch_second > spike_second:
        windows.append(SignalWindow(spike_second, catch_second, "autoscale_lag"))
    return windows
