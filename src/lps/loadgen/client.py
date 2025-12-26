from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from lps.config import RetryConfig, TargetConfig
from lps.metrics import ErrorType, RequestEvent


@dataclass(frozen=True, slots=True)
class ClientResponse:
    event: RequestEvent
    success: bool


async def send_request(
    client: httpx.AsyncClient,
    run_id: str,
    target: TargetConfig,
    retry: RetryConfig,
) -> ClientResponse:
    start_wall = time.time()
    start_mono = time.perf_counter()
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = await client.request(
                target.method,
                target.base_url,
                headers=target.headers,
                timeout=target.timeout_sec,
            )
            latency_ms = (time.perf_counter() - start_mono) * 1000.0
            event = RequestEvent(
                run_id=run_id,
                wall_time=start_wall,
                mono_time=time.perf_counter(),
                latency_ms=latency_ms,
                status_code=resp.status_code,
                error_type=None,
                bytes_sent=len(resp.request.content or b""),
                bytes_received=len(resp.content or b""),
            )
            return ClientResponse(event=event, success=resp.is_success)
        except httpx.TimeoutException:
            err = ErrorType.TIMEOUT
        except httpx.ConnectError:
            err = ErrorType.CONNECT
        except httpx.ReadError:
            err = ErrorType.READ
        except httpx.HTTPError:
            err = ErrorType.OTHER
        latency_ms = (time.perf_counter() - start_mono) * 1000.0
        event = RequestEvent(
            run_id=run_id,
            wall_time=start_wall,
            mono_time=time.perf_counter(),
            latency_ms=latency_ms,
            status_code=None,
            error_type=err,
            bytes_sent=0,
            bytes_received=0,
        )
        if not retry.enabled or attempt > retry.max_retries:
            return ClientResponse(event=event, success=False)
        delay = min(retry.max_delay_sec, retry.base_delay_sec * (2 ** (attempt - 1)))
        await asyncio.sleep(delay)
