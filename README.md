# Load Pattern Simulator (LPS)

LPS is a production-quality MVP for generating realistic HTTP traffic patterns, capturing per-request metrics, and visualizing behavior under load. Think of it as **k6 + experiment runner + analytics UI**, built in typed Python with clean architecture and analytics-first storage.

## Why it’s useful

- Reproduce traffic patterns (bursty, diurnal, viral spikes) deterministically
- Capture per-request latency and error metrics
- Analyze overload signals and regressions between runs
- Share polished reports via a Streamlit dashboard

## Quick start

```bash
uv sync
uv run streamlit run src/lps/ui/app.py
```

Runs are stored in `.lps/lps.duckdb`.

## Viral spike demo in <5 minutes

1. Start the UI:
   ```bash
   uv run streamlit run src/lps/ui/app.py
   ```
2. Use the defaults and set the target URL (e.g. `https://httpbin.org/get`).
3. Choose **Viral Spike**, set duration to 300s, and click **Start run**.
4. Inspect requested vs achieved RPS, latency percentiles, and error rate.
5. Run a second experiment and use **Run Comparison** to spot regressions.

## CLI usage

```bash
uv run lps --target https://httpbin.org/get --pattern viral --duration 180
```

## Architecture overview

- `lps/patterns/`: traffic patterns and schedule generation
- `lps/loadgen/`: async load engine (open-loop and closed-loop)
- `lps/metrics/`: per-request events and per-second aggregation
- `lps/storage/`: DuckDB storage optimized for analytics
- `lps/analysis/`: heuristics for overload signals and run comparisons
- `lps/ui/`: Streamlit dashboard with Plotly charts

## Testing

```bash
uv run pytest
```

## V2 hooks (designed for)

- Distributed workers
- gRPC targets
- CSV/DSL pattern ingestion
- Prometheus export
- Advanced overload annotations
