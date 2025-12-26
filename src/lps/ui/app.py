from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lps.analysis import autoscaling_lag, compare_runs, overload_indicator, queueing_indicator
from lps.config import (
    BurstyConfig,
    CircuitBreakerConfig,
    DiurnalConfig,
    LoadModel,
    PatternConfig,
    PatternType,
    RetryConfig,
    RunConfig,
    TargetConfig,
    ViralSpikeConfig,
)
from lps.loadgen.runner import run_experiment
from lps.storage import default_storage


st.set_page_config(page_title="Load Pattern Simulator", layout="wide")

storage = default_storage()


@st.cache_data
def _load_runs() -> pd.DataFrame:
    return storage.list_runs()


def _render_header() -> None:
    st.title("Load Pattern Simulator")
    st.caption("Traffic patterns, load generation, and analytics for HTTP services.")


def _build_config() -> RunConfig:
    with st.sidebar:
        st.header("Run Configuration")
        target_url = st.text_input("Target URL", "https://httpbin.org/get")
        duration = st.slider("Duration (sec)", 30, 1800, 300)
        load_model = st.selectbox("Load Model", ["open_loop", "closed_loop"])
        workers = st.slider("Closed-loop workers", 5, 200, 50)
        pattern_type = st.selectbox("Pattern", ["bursty", "diurnal", "viral_spike"])
        seed = st.number_input("Seed", min_value=1, max_value=9999, value=7)
        notes = st.text_input("Notes", "")

        st.subheader("Resilience knobs")
        retry_enabled = st.checkbox("Retries", value=False)
        breaker_enabled = st.checkbox("Circuit breaker", value=False)

    pattern_config = _pattern_config(pattern_type)
    retry = RetryConfig(enabled=retry_enabled)
    breaker = CircuitBreakerConfig(enabled=breaker_enabled)
    return RunConfig(
        target=TargetConfig(base_url=target_url),
        pattern=pattern_config,
        duration_sec=duration,
        load_model=LoadModel(load_model),
        closed_loop_workers=workers,
        seed=seed,
        retry=retry,
        circuit_breaker=breaker,
        notes=notes,
    )


def _pattern_config(pattern_type: str) -> PatternConfig:
    with st.sidebar:
        st.subheader("Pattern parameters")
        if pattern_type == "bursty":
            baseline = st.number_input("Baseline RPS", min_value=1.0, value=50.0)
            burst = st.number_input("Burst RPS", min_value=1.0, value=500.0)
            duration = st.number_input("Burst duration (sec)", min_value=1, value=10)
            interval = st.number_input("Burst interval (sec)", min_value=1, value=120)
            jitter = st.slider("Jitter %", 0.0, 0.3, 0.05)
            cfg = BurstyConfig(
                baseline_rps=baseline,
                burst_rps=burst,
                burst_duration_sec=duration,
                burst_interval_sec=interval,
                jitter_pct=jitter,
            )
            return PatternConfig(PatternType.BURSTY, asdict(cfg))
        if pattern_type == "diurnal":
            min_rps = st.number_input("Min RPS", min_value=1.0, value=20.0)
            max_rps = st.number_input("Max RPS", min_value=1.0, value=300.0)
            cycle = st.number_input("Cycle duration (sec)", min_value=60, value=1800)
            shape = st.selectbox("Shape", ["sine", "gaussian", "commuter"])
            cfg = DiurnalConfig(min_rps=min_rps, max_rps=max_rps, cycle_duration_sec=cycle, shape=shape)
            return PatternConfig(PatternType.DIURNAL, asdict(cfg))
        baseline = st.number_input("Baseline RPS", min_value=1.0, value=20.0)
        multiplier = st.number_input("Spike multiplier", min_value=2.0, value=30.0)
        ramp = st.number_input("Ramp up (sec)", min_value=1, value=30)
        hold = st.number_input("Peak hold (sec)", min_value=1, value=60)
        half_life = st.number_input("Decay half-life (sec)", min_value=1, value=60)
        cfg = ViralSpikeConfig(
            baseline_rps=baseline,
            spike_multiplier=multiplier,
            ramp_up_sec=ramp,
            peak_hold_sec=hold,
            decay_half_life_sec=half_life,
        )
        return PatternConfig(PatternType.VIRAL, asdict(cfg))


def _run_button(config: RunConfig) -> None:
    if st.sidebar.button("Start run"):
        progress = st.sidebar.progress(0, text="Running...")

        async def on_progress(step: int, total: int) -> None:
            progress.progress(min(1.0, step / total))

        run_id = asyncio.run(run_experiment(config, storage, progress=on_progress))
        st.sidebar.success(f"Run completed: {run_id}")
        st.cache_data.clear()


def _plot_requested_vs_achieved(per_second: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=per_second["second"],
            y=per_second["requested_rps"],
            name="Requested RPS",
            mode="lines",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=per_second["second"],
            y=per_second["achieved_rps"],
            name="Achieved RPS",
            mode="lines",
        )
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _plot_latency(per_second: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, label in [("p50_ms", "p50"), ("p95_ms", "p95"), ("p99_ms", "p99")]:
        fig.add_trace(go.Scatter(x=per_second["second"], y=per_second[col], name=label, mode="lines"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _plot_error_stack(events: pd.DataFrame, duration: int) -> go.Figure:
    if events.empty:
        return go.Figure()
    events = events.copy()
    start = events["mono_time"].min()
    events["second"] = (events["mono_time"] - start).astype(float).round(0).astype(int)
    events = events[events["error_type"].notna()]
    if events.empty:
        return go.Figure()
    grouped = events.groupby(["second", "error_type"]).size().reset_index(name="count")
    fig = px.area(
        grouped,
        x="second",
        y="count",
        color="error_type",
        title="Errors by type",
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _plot_latency_hist(events: pd.DataFrame, per_second: pd.DataFrame) -> go.Figure:
    if events.empty or per_second.empty:
        return go.Figure()
    peak_second = int(per_second.loc[per_second["p99_ms"].idxmax(), "second"])
    start = events["mono_time"].min()
    relative_sec = (events["mono_time"] - start).astype(int)
    window = events[(relative_sec >= peak_second) & (relative_sec <= peak_second + 5)]
    fig = px.histogram(window, x="latency_ms", nbins=30, title="Latency distribution (peak window)")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _plot_slo_breach(per_second: pd.DataFrame, threshold_ms: float) -> go.Figure:
    breach = per_second[per_second["p99_ms"] > threshold_ms]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=breach["second"],
            y=[1] * len(breach),
            name="SLO breach",
        )
    )
    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(visible=False),
    )
    return fig


def _render_signals(per_second: pd.DataFrame) -> None:
    queue = queueing_indicator(per_second)
    overload = overload_indicator(per_second)
    lag = autoscaling_lag(per_second)
    if not queue and not overload and not lag:
        st.info("No derived signals detected")
        return
    for signal in queue + overload + lag:
        st.warning(f"{signal.label}: {signal.start_sec}s → {signal.end_sec}s")


def _render_run_view(run_id: str) -> None:
    per_second = storage.load_per_second(run_id)
    events = storage.load_request_events(run_id)
    meta = storage.load_run_meta(run_id) or {}
    st.subheader(f"Run {run_id}")
    st.caption(meta.get("notes", ""))

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(_plot_requested_vs_achieved(per_second), use_container_width=True)
    with col2:
        st.plotly_chart(_plot_latency(per_second), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(_plot_error_stack(events, len(per_second)), use_container_width=True)
    with col4:
        st.plotly_chart(_plot_latency_hist(events, per_second), use_container_width=True)

    threshold = st.slider("SLO threshold (p99 ms)", 50, 2000, 500)
    st.plotly_chart(_plot_slo_breach(per_second, threshold), use_container_width=True)
    _render_signals(per_second)


def _render_comparison() -> None:
    runs = _load_runs()
    if runs.empty:
        return
    run_ids = runs["run_id"].tolist()
    st.subheader("Run Comparison")
    base = st.selectbox("Baseline run", run_ids, index=0)
    candidate = st.selectbox("Candidate run", run_ids, index=min(1, len(run_ids) - 1))
    if base == candidate:
        st.info("Select two different runs for comparison")
        return
    base_df = storage.load_per_second(base)
    cand_df = storage.load_per_second(candidate)
    merged = base_df.merge(cand_df, on="second", suffixes=("_base", "_cand"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=merged["second"], y=merged["achieved_rps_base"], name=f"{base} achieved"))
    fig.add_trace(go.Scatter(x=merged["second"], y=merged["achieved_rps_cand"], name=f"{candidate} achieved"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    regressions = compare_runs(base_df, cand_df)
    if not regressions:
        st.success("No regressions detected")
    else:
        for reg in regressions:
            st.error(f"{reg.message} ({reg.delta_pct:.1f}% on {reg.metric})")


def main() -> None:
    _render_header()
    config = _build_config()
    _run_button(config)

    runs = _load_runs()
    if runs.empty:
        st.info("No runs yet. Start one from the sidebar.")
        return
    selected_run = st.selectbox("Select run", runs["run_id"].tolist())
    _render_run_view(selected_run)
    _render_comparison()


if __name__ == "__main__":
    main()
