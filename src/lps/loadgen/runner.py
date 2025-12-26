from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable

import httpx

from lps.config import LoadModel, RunConfig
from lps.loadgen.breaker import CircuitBreaker
from lps.loadgen.client import ClientResponse, send_request
from lps.metrics import RequestEvent, aggregate_per_second
from lps.patterns import schedule_for
from lps.storage import Storage


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    events: list[RequestEvent]
    requested_rates: list[float]
    started_mono: float


ProgressCallback = Callable[[int, int], Awaitable[None]]


def _new_run_id() -> str:
    return uuid.uuid4().hex


async def run_experiment(
    config: RunConfig,
    storage: Storage,
    progress: ProgressCallback | None = None,
) -> str:
    run_id = config.run_id or _new_run_id()
    if storage.run_exists(run_id):
        msg = f"Run {run_id} already exists"
        raise ValueError(msg)
    schedule = schedule_for(config.pattern, config.duration_sec, config.seed)
    run_result = await _execute_load(run_id, config, schedule.rates_per_sec, progress)
    per_second = aggregate_per_second(
        run_id,
        run_result.events,
        run_result.requested_rates,
        run_result.started_mono,
    )
    storage.save_run(config, run_id, run_result.events, per_second)
    return run_id


async def _execute_load(
    run_id: str,
    config: RunConfig,
    requested_rates: list[float],
    progress: ProgressCallback | None,
) -> RunResult:
    events: list[RequestEvent] = []
    started_mono = time.perf_counter()
    breaker = None
    if config.circuit_breaker.enabled:
        breaker = CircuitBreaker(
            window_size=config.circuit_breaker.window_size,
            error_rate_threshold=config.circuit_breaker.error_rate_threshold,
            open_cooldown_sec=config.circuit_breaker.open_cooldown_sec,
        )
    async with httpx.AsyncClient() as client:
        if config.load_model is LoadModel.CLOSED_LOOP:
            await _closed_loop(
                client,
                run_id,
                config,
                requested_rates,
                events,
                breaker,
                progress,
                started_mono,
            )
        else:
            await _open_loop(
                client,
                run_id,
                config,
                requested_rates,
                events,
                breaker,
                progress,
                started_mono,
            )
    return RunResult(run_id=run_id, events=events, requested_rates=requested_rates, started_mono=started_mono)


async def _open_loop(
    client: httpx.AsyncClient,
    run_id: str,
    config: RunConfig,
    requested_rates: list[float],
    events: list[RequestEvent],
    breaker: CircuitBreaker | None,
    progress: ProgressCallback | None,
    started_mono: float,
) -> None:
    tasks: list[asyncio.Task[None]] = []
    lock = asyncio.Lock()
    rng = random.Random(config.seed)
    for second, rate in enumerate(requested_rates):
        n = int(rate)
        if rate - n > 0 and rng.random() < (rate - n):
            n += 1
        if n <= 0:
            await _sleep_until_next_second(started_mono, second)
            if progress:
                await progress(second + 1, len(requested_rates))
            continue
        for i in range(n):
            offset = (i / n) if n > 0 else 0.0
            tasks.append(
                asyncio.create_task(
                    _schedule_one(
                        client,
                        run_id,
                        config,
                        events,
                        breaker,
                        started_mono,
                        lock,
                        second + offset,
                    )
                )
            )
        await _sleep_until_next_second(started_mono, second)
        if progress:
            await progress(second + 1, len(requested_rates))
    if tasks:
        await asyncio.gather(*tasks)


async def _closed_loop(
    client: httpx.AsyncClient,
    run_id: str,
    config: RunConfig,
    requested_rates: list[float],
    events: list[RequestEvent],
    breaker: CircuitBreaker | None,
    progress: ProgressCallback | None,
    started_mono: float,
) -> None:
    stop_at = started_mono + len(requested_rates)
    lock = asyncio.Lock()

    async def worker(worker_id: int) -> None:
        while time.perf_counter() < stop_at:
            elapsed = time.perf_counter() - started_mono
            rate = _rate_for_time(requested_rates, elapsed)
            if rate <= 0:
                await asyncio.sleep(0.05)
                continue
            per_worker_interval = max(0.0, config.closed_loop_workers / rate)
            await _maybe_send(
                client,
                run_id,
                config,
                events,
                breaker,
                lock,
            )
            await asyncio.sleep(per_worker_interval)

    tasks = [asyncio.create_task(worker(i)) for i in range(config.closed_loop_workers)]
    if progress:
        for second in range(len(requested_rates)):
            await _sleep_until_next_second(started_mono, second)
            await progress(second + 1, len(requested_rates))
    await asyncio.gather(*tasks)


async def _schedule_one(
    client: httpx.AsyncClient,
    run_id: str,
    config: RunConfig,
    events: list[RequestEvent],
    breaker: CircuitBreaker | None,
    started_mono: float,
    lock: asyncio.Lock,
    offset_sec: float,
) -> None:
    await _sleep_until_time(started_mono + offset_sec)
    await _maybe_send(client, run_id, config, events, breaker, lock)


async def _maybe_send(
    client: httpx.AsyncClient,
    run_id: str,
    config: RunConfig,
    events: list[RequestEvent],
    breaker: CircuitBreaker | None,
    lock: asyncio.Lock,
) -> None:
    if breaker is not None and not breaker.allow_request():
        return
    response = await send_request(client, run_id, config.target, config.retry)
    if breaker is not None:
        breaker.record(response.success)
    async with lock:
        events.append(response.event)


async def _sleep_until_next_second(started_mono: float, second: int) -> None:
    target = started_mono + second + 1
    await _sleep_until_time(target)


async def _sleep_until_time(target: float) -> None:
    delay = max(0.0, target - time.perf_counter())
    if delay > 0:
        await asyncio.sleep(delay)


def _rate_for_time(rates: list[float], elapsed: float) -> float:
    idx = int(elapsed)
    if idx < 0 or idx >= len(rates):
        return 0.0
    return rates[idx]
