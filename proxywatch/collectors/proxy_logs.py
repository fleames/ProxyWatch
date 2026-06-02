"""Proxy log collector — streams docker logs from the socks5 container."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from proxywatch.collectors.base import BaseCollector


class ProxyLogsCollector(BaseCollector):
    """Streams docker logs from the proxy container.

    Maintains a ring buffer of the last N log lines with color-coded
    log levels (INFO, WARN, ERR).
    """

    def __init__(
        self,
        data_store: dict[str, Any],
        container_name: str = "socks5",
        max_lines: int = 50,
        interval: float = 1.0,
    ) -> None:
        super().__init__(data_store, interval)
        self.container_name = container_name
        self.max_lines = max_lines
        self._log_buffer: deque[dict[str, str]] = deque(maxlen=max_lines)
        self._stream_task: asyncio.Task[None] | None = None
        self._client = None

    def _get_client(self):
        """Lazy-load docker client."""
        if self._client is None:
            try:
                import docker

                self._client = docker.from_env()
            except Exception:
                self._client = None
        return self._client

    def _parse_log_level(self, line: str) -> str:
        """Determine log level from a log line."""
        upper = line.upper()
        if "ERR" in upper or "ERROR" in upper or "FAIL" in upper or "BROKEN" in upper or "TIMED OUT" in upper:
            return "error"
        if "WARN" in upper or "WARNING" in upper:
            return "warning"
        return "info"

    async def _stream_logs(self) -> None:
        """Async wrapper around docker logs stream."""
        client = self._get_client()
        if client is None:
            return

        try:
            container = await asyncio.to_thread(client.containers.get, self.container_name)
        except Exception:
            return

        try:
            # docker logs -f --tail 50
            log_gen = await asyncio.to_thread(
                container.logs,
                stream=True,
                follow=True,
                tail=self.max_lines,
                timestamps=True,
            )
        except Exception:
            return

        # Process the generator
        for chunk in log_gen:
            if not self._running:
                break
            try:
                if isinstance(chunk, bytes):
                    line = chunk.decode("utf-8", errors="replace").strip()
                else:
                    line = str(chunk).strip()
                if line:
                    level = self._parse_log_level(line)
                    self._log_buffer.append({"text": line, "level": level})
                    self.data_store.update({"proxy_logs": list(self._log_buffer)})
            except Exception:
                continue

    async def _start_stream(self) -> None:
        """Start the log streaming background task."""
        if self._stream_task is not None and not self._stream_task.done():
            return
        self._stream_task = asyncio.create_task(self._stream_logs())

    async def start(self) -> None:
        """Start the log collector with streaming."""
        if self._running:
            return
        self._running = True
        await self._start_stream()

    async def stop(self) -> None:
        """Stop the log collector."""
        self._running = False
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    async def collect(self) -> None:
        """Periodic check to ensure log stream is running."""
        if self._stream_task is None or self._stream_task.done():
            await self._start_stream()

        # Push current buffer to data store
        self.data_store.update({"proxy_logs": list(self._log_buffer)})

    def clear_logs(self) -> None:
        """Clear the log buffer."""
        self._log_buffer.clear()
        self.data_store.update({"proxy_logs": []})