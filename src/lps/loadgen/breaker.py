from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time


@dataclass(slots=True)
class CircuitBreaker:
    window_size: int
    error_rate_threshold: float
    open_cooldown_sec: float
    state: str = "closed"  # closed | open | half_open
    _history: deque[bool] = deque()
    _opened_at: float | None = None

    def allow_request(self) -> bool:
        if self.state == "open":
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= self.open_cooldown_sec:
                self.state = "half_open"
                return True
            return False
        return True

    def record(self, success: bool) -> None:
        if self.state == "half_open":
            if success:
                self.state = "closed"
                self._history.clear()
                return
            self._open()
            return
        self._history.append(success)
        if len(self._history) > self.window_size:
            self._history.popleft()
        self._evaluate()

    def _evaluate(self) -> None:
        if len(self._history) < self.window_size:
            return
        error_rate = 1.0 - (sum(self._history) / len(self._history))
        if error_rate >= self.error_rate_threshold:
            self._open()

    def _open(self) -> None:
        self.state = "open"
        self._opened_at = time.monotonic()
        self._history.clear()
