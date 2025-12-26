from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

from lps.config import RunConfig
from lps.metrics import PerSecondMetrics, RequestEvent


@dataclass(slots=True)
class Storage:
    db_path: Path

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS run_meta (
                    run_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP,
                    config_json TEXT,
                    notes TEXT
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS request_events (
                    run_id TEXT,
                    wall_time DOUBLE,
                    mono_time DOUBLE,
                    latency_ms DOUBLE,
                    status_code INTEGER,
                    error_type TEXT,
                    bytes_sent INTEGER,
                    bytes_received INTEGER
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS per_second (
                    run_id TEXT,
                    second INTEGER,
                    requested_rps DOUBLE,
                    achieved_rps DOUBLE,
                    p50_ms DOUBLE,
                    p95_ms DOUBLE,
                    p99_ms DOUBLE,
                    error_rate DOUBLE,
                    timeout_rate DOUBLE
                );
                """
            )

    def run_exists(self, run_id: str) -> bool:
        with self._connect() as con:
            result = con.execute(
                "SELECT COUNT(*) FROM run_meta WHERE run_id = ?",
                [run_id],
            ).fetchone()
            return bool(result and result[0] > 0)

    def save_run(
        self,
        config: RunConfig,
        run_id: str,
        events: Iterable[RequestEvent],
        per_second: Iterable[PerSecondMetrics],
    ) -> None:
        config_json = json.dumps(config.to_metadata())
        with self._connect() as con:
            con.execute(
                "INSERT INTO run_meta VALUES (?, ?, ?, ?)",
                [run_id, config.created_at, config_json, config.notes],
            )
            events_df = pd.DataFrame(
                [
                    {
                        "run_id": e.run_id,
                        "wall_time": e.wall_time,
                        "mono_time": e.mono_time,
                        "latency_ms": e.latency_ms,
                        "status_code": e.status_code,
                        "error_type": e.error_type.value if e.error_type else None,
                        "bytes_sent": e.bytes_sent,
                        "bytes_received": e.bytes_received,
                    }
                    for e in events
                ]
            )
            if not events_df.empty:
                con.execute("INSERT INTO request_events SELECT * FROM events_df")
            per_df = pd.DataFrame(
                [
                    {
                        "run_id": m.run_id,
                        "second": m.second,
                        "requested_rps": m.requested_rps,
                        "achieved_rps": m.achieved_rps,
                        "p50_ms": m.p50_ms,
                        "p95_ms": m.p95_ms,
                        "p99_ms": m.p99_ms,
                        "error_rate": m.error_rate,
                        "timeout_rate": m.timeout_rate,
                    }
                    for m in per_second
                ]
            )
            if not per_df.empty:
                con.execute("INSERT INTO per_second SELECT * FROM per_df")

    def list_runs(self) -> pd.DataFrame:
        with self._connect() as con:
            return con.execute(
                "SELECT run_id, created_at, notes FROM run_meta ORDER BY created_at DESC"
            ).fetchdf()

    def load_run_meta(self, run_id: str) -> dict[str, object] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT config_json FROM run_meta WHERE run_id = ?",
                [run_id],
            ).fetchone()
            if not row:
                return None
            return json.loads(row[0])

    def load_per_second(self, run_id: str) -> pd.DataFrame:
        with self._connect() as con:
            return con.execute(
                "SELECT * FROM per_second WHERE run_id = ? ORDER BY second",
                [run_id],
            ).fetchdf()

    def load_request_events(self, run_id: str) -> pd.DataFrame:
        with self._connect() as con:
            return con.execute(
                "SELECT * FROM request_events WHERE run_id = ?",
                [run_id],
            ).fetchdf()
