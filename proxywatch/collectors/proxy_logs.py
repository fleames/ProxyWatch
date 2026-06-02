"""Proxy log collector — streams docker logs from the socks5 container (local + remote)."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, TYPE_CHECKING

from proxywatch.collectors.base import BaseCollector

if TYPE_CHECKING:
    from proxywatch.remote import RemoteClient


class ProxyLogsCollector(BaseCollector):
    """Streams docker logs from the proxy container."""

    def __init__(
        self,
        data_store: dict[str, Any],
        container_name: str = "socks5",
        max_lines: int = 50,
        interval: float = 1.0,
        remote_client: "RemoteClient | None" = None,
    ) -> None:
        super().__init__(data_store, interval)
        self.container_name = container_name
        self.max_lines = max_lines
        self._remote = remote_client
        self._log_buffer: deque[dict[str, str]] = deque(maxlen=max_lines)
        self._stream_task: asyncio.Task[None] | None = None
        self._client = None

    def _parse_log_level(self, line: str) -> str:
        """Determine log level from a log line."""
        upper = line.upper()
        if "ERR" in upper or "ERROR" in upper or "FAIL" in upper or "BROKEN" in upper or "TIMED OUT" in upper:
            return "error"
        if "WARN" in upper or "WARNING" in upper:
            return "warning"
        return "info"

    async def _collect_local(self) -> None:
        """Stream logs via Docker SDK (local mode)."""
        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(self.container_name)
            log_gen = container.logs(stream=True, follow=True, tail=self.max_lines, timestamps=True)
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
        except Exception:
            pass

    async def _collect_remote(self) -> None:
        """Fetch logs via SSH docker logs command (polling)."""
        if self._remote is None:
            return

        connected = await self._remote.ensure_connected()
        if not connected:
            return

        cmd = f"docker logs --tail {self.max_lines} {self.container_name} 2>/dev/null || echo ''"
        result = await self._remote.run(cmd, timeout=10.0)

        stdout = result.get("stdout", "") or ""
        lines = stdout.splitlines() if stdout else []

        self._log_buffer.clear()
        for line in lines:
            line = line.strip()
            if line:
                level = self._parse_log_level(line)
                self._log_buffer.append({"text": line, "level": level})

        self.data_store.update({"proxy_logs": list(self._log_buffer)})

    async def _start_local_stream(self) -> None:
        """Start the local Docker log streaming background task."""
        if self._stream_task is not None and not self._stream_task.done():
            return
        self._stream_task = asyncio.create_task(self._collect_local())

    async def start(self) -> None:
        """Start the log collector."""
        if self._running:
            return
        self._running = True
        if self._remote:
            # Remote mode: just do first poll, intervals handle the rest
            await self._collect_remote()
        else:
            await self._start_local_stream()

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
        """Periodic check — refresh logs in remote mode, ensure stream in local mode."""
        if self._remote:
            await self._collect_remote()
        elif self._stream_task is None or self._stream_task.done():
            await self._start_local_stream()

        # Push current buffer to data store
        self.data_store.update({"proxy_logs": list(self._log_buffer)})

    def clear_logs(self) -> None:
        """Clear the log buffer."""
        self._log_buffer.clear()
        self.data_store.update({"proxy_logs": []})