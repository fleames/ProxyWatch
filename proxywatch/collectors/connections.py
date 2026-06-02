"""Live client connection collector — tracks active TCP connections (local + remote)."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, TYPE_CHECKING

from proxywatch.collectors.base import BaseCollector
from proxywatch.utils.net_parser import (
    get_connection_summary,
    get_connection_summary_from_text,
)

if TYPE_CHECKING:
    from proxywatch.remote import RemoteClient


class ConnectionCollector(BaseCollector):
    """Collects active TCP connections on the proxy port."""

    def __init__(
        self,
        data_store: dict[str, Any],
        proxy_port: int,
        interval: float = 1.0,
        remote_client: "RemoteClient | None" = None,
    ) -> None:
        super().__init__(data_store, interval)
        self.proxy_port = proxy_port
        self._remote = remote_client
        self._connection_start_times: dict[str, float] = {}
        self._last_conn_count = 0
        self._conn_rate_samples: list[float] = []

    async def _collect_local(self) -> None:
        """Read /proc/net/tcp and enumerate active proxy connections."""
        established, listening, connections = get_connection_summary(self.proxy_port)
        self._process_connections(established, listening, connections)

    async def _collect_remote(self) -> None:
        """Read remote /proc/net/tcp via SSH."""
        if self._remote is None:
            return

        connected = await self._remote.ensure_connected()
        if not connected:
            return

        commands = {
            "tcp": "cat /proc/net/tcp",
            "tcp6": "cat /proc/net/tcp6",
        }

        results = await self._remote.run_many(commands, timeout=10.0)

        tcp_text = results["tcp"]["stdout"] or ""
        tcp6_text = results["tcp6"]["stdout"] or ""

        established, listening, connections = get_connection_summary_from_text(
            tcp_text, tcp6_text, self.proxy_port
        )
        self._process_connections(established, listening, connections)

    def _process_connections(
        self,
        established: int,
        listening: int,
        connections: list[dict[str, object]],
    ) -> None:
        """Process connection data into data store format."""
        now = time.time()

        current_inodes: set[str] = set()
        conn_details: list[dict[str, Any]] = []

        for conn in connections:
            rem_addr = str(conn["rem_address"])
            rem_port = int(conn["rem_port"])
            inode = str(conn["inode"])
            local_addr = str(conn["local_address"])

            conn_key = f"{rem_addr}:{rem_port}"
            current_inodes.add(conn_key)

            if conn_key not in self._connection_start_times:
                self._connection_start_times[conn_key] = now

            duration = now - self._connection_start_times[conn_key]

            conn_details.append({
                "source_ip": rem_addr,
                "source_port": rem_port,
                "destination_ip": local_addr,
                "destination_port": self.proxy_port,
                "duration": duration,
                "tx_queue": int(conn["tx_queue"]),
                "rx_queue": int(conn["rx_queue"]),
                "inode": inode,
                "state": int(conn["st"]),
            })

        # Clean up stale connection start times
        stale = set(self._connection_start_times.keys()) - current_inodes
        for key in stale:
            del self._connection_start_times[key]

        # Track connections per minute
        conn_count = len(connections)
        delta = conn_count - self._last_conn_count
        self._conn_rate_samples.append(delta)
        if len(self._conn_rate_samples) > 60:
            self._conn_rate_samples.pop(0)
        self._last_conn_count = conn_count

        requests_per_minute = sum(self._conn_rate_samples)

        # Build per-IP connection counts
        ip_counts: dict[str, int] = defaultdict(int)
        for conn in conn_details:
            ip_counts[conn["source_ip"]] += 1

        self.data_store.update({
            "connections_active": conn_count,
            "connections_listening": listening,
            "connections_details": conn_details,
            "connections_ip_counts": dict(ip_counts),
            "requests_per_minute": requests_per_minute,
            "total_connections_tracked": len(self._connection_start_times),
        })

    async def collect(self) -> None:
        """Collect connection data."""
        if self._remote:
            await self._collect_remote()
        else:
            await self._collect_local()