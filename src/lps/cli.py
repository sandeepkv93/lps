from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict

from lps.config import (
    BurstyConfig,
    DiurnalConfig,
    LoadModel,
    PatternConfig,
    PatternType,
    RunConfig,
    TargetConfig,
    ViralSpikeConfig,
)
from lps.loadgen.runner import run_experiment
from lps.storage import default_storage


def _build_pattern(args: argparse.Namespace) -> PatternConfig:
    if args.pattern == "bursty":
        cfg = BurstyConfig(
            baseline_rps=args.baseline_rps,
            burst_rps=args.burst_rps,
            burst_duration_sec=args.burst_duration_sec,
            burst_interval_sec=args.burst_interval_sec,
            jitter_pct=args.jitter_pct,
        )
        return PatternConfig(PatternType.BURSTY, asdict(cfg))
    if args.pattern == "diurnal":
        cfg = DiurnalConfig(
            min_rps=args.min_rps,
            max_rps=args.max_rps,
            cycle_duration_sec=args.cycle_duration_sec,
            shape=args.shape,
        )
        return PatternConfig(PatternType.DIURNAL, asdict(cfg))
    cfg = ViralSpikeConfig(
        baseline_rps=args.baseline_rps,
        spike_multiplier=args.spike_multiplier,
        ramp_up_sec=args.ramp_up_sec,
        peak_hold_sec=args.peak_hold_sec,
        decay_half_life_sec=args.decay_half_life_sec,
    )
    return PatternConfig(PatternType.VIRAL, asdict(cfg))


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Pattern Simulator")
    parser.add_argument("--target", required=True, help="Target URL")
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--pattern", choices=["bursty", "diurnal", "viral"], default="viral")
    parser.add_argument("--load-model", choices=["open_loop", "closed_loop"], default="open_loop")
    parser.add_argument("--workers", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)

    parser.add_argument("--baseline-rps", type=float, default=30.0)
    parser.add_argument("--burst-rps", type=float, default=500.0)
    parser.add_argument("--burst-duration-sec", type=int, default=10)
    parser.add_argument("--burst-interval-sec", type=int, default=120)
    parser.add_argument("--jitter-pct", type=float, default=0.05)

    parser.add_argument("--min-rps", type=float, default=20.0)
    parser.add_argument("--max-rps", type=float, default=300.0)
    parser.add_argument("--cycle-duration-sec", type=int, default=1800)
    parser.add_argument("--shape", choices=["sine", "gaussian", "commuter"], default="sine")

    parser.add_argument("--spike-multiplier", type=float, default=100.0)
    parser.add_argument("--ramp-up-sec", type=int, default=45)
    parser.add_argument("--peak-hold-sec", type=int, default=120)
    parser.add_argument("--decay-half-life-sec", type=int, default=90)

    args = parser.parse_args()

    pattern = _build_pattern(args)
    target = TargetConfig(base_url=args.target)
    config = RunConfig(
        target=target,
        pattern=pattern,
        duration_sec=args.duration,
        load_model=LoadModel(args.load_model),
        closed_loop_workers=args.workers,
        seed=args.seed,
    )
    storage = default_storage()
    run_id = asyncio.run(run_experiment(config, storage))
    print(f"Run complete: {run_id}")


if __name__ == "__main__":
    main()
