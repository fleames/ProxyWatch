"""Base classes for async data collectors."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """Abstract base for all async data collectors.

    Each collector runs its own polling loop and stores the latest snapshot
    in a shared DataStore instance.
    """

    def __init__(self, data_store: "DataStore", interval: float = 1.0) -> None:
        self.data_store = data_store
        self.interval = interval
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @abstractmethod
    async def collect(self) -> None:
        """Perform one data collection cycle and update the data store.

        Subclasses must implement this method.
        """

    async def _loop(self) -> None:
        """Internal async loop that calls collect() at the configured interval."""
        while self._running:
            try:
                await self.collect()
            except Exception:
                # Collectors must be resilient — a single failure should not
                # crash the dashboard.  We deliberately swallow exceptions here.
                pass
            await asyncio.sleep(self.interval)

    async def start(self) -> None:
        """Start the collector's polling loop."""
        if self._running:
            return
        self._running = True
        # Run first collection immediately
        try:
            await self.collect()
        except Exception:
            pass
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the collector's polling loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


class DataStore:
    """Synchronous dictionary wrapper for sharing data between collectors and UI.

    All operations are synchronous because Textual and all collectors run on
    the same asyncio event loop (single-threaded cooperative multitasking).
    Python dict operations are atomic at the coroutine yield point level.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._start_time = time.time()

    def update(self, updates: dict[str, Any]) -> None:
        """Merge updates into the data store."""
        self._data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a single value from the data store."""
        return self._data.get(key, default)

    def get_sync(self, key: str, default: Any = None) -> Any:
        """Read a single value (alias for get)."""
        return self._data.get(key, default)

    def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the entire data store."""
        return dict(self._data)

    @property
    def uptime(self) -> float:
        """Seconds since the DataStore was created."""
        return time.time() - self._start_time