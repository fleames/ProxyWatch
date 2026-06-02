"""Live client connection collector — tracks active TCP connections to proxy port."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from proxywatch.collectors.base import BaseCollector
from proxywatch.utils.net_parser import get_connection_summary


class ConnectionCollector(BaseCollector):
    """Collects active TCP connections on the proxy port.

    Tracks per-IP connection counts and maintains a mapping of
    inode -> connection detail for per-connection RX/TX estimation.
    """

    def __init__(
        self,
        data_store: dict[str, Any],
        proxy_port: int,
        interval: float = 1.0,
    ) -> None:
        super().__init__(data_store, interval)
        self.proxy_port = proxy_port
        self._connection_start_times: dict[str, float] = {}
        self._last_conn_count = 0
        self._conn_rate_samples: list[float] = []

    async def collect(self) -> None:
        """Read /proc/net/tcp and enumerate active proxy connections."""
        established, listening, connections = get_connection_summary(self.proxy_port)

        now = time.time()

        # Track per-connection start times
        current_inodes: set[str] = set()
        conn_details: list[dict[str, Any]] = []

        for conn in connections:
            rem_addr = str(conn["rem_address"])
            rem_port = int(conn["rem_port"])
            inode = str(conn["inode"])
            local_addr = str(conn["local_address"])

            # Use remote IP + remote port as key (inode changes per connection)
            conn_key = f"{rem_addr}:{rem_port}"
            current_inodes.add(conn_key)

            if conn_key not in self._connection_start_times:
                self._connection_start_times[conn_key] = now

            duration = now - self._connection_start_times[conn_key]

            conn_details.append(
                {
                    "source_ip": rem_addr,
                    "source_port": rem_port,
                    "destination_ip": local_addr,
                    "destination_port": self.proxy_port,
                    "duration": duration,
                    "tx_queue": int(conn["tx_queue"]),
                    "rx_queue": int(conn["rx_queue"]),
                    "inode": inode,
                    "state": int(conn["st"]),
                }
            )

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

        self.data_store.update(
            {
                "connections_active": conn_count,
                "connections_listening": listening,
                "connections_details": conn_details,
                "connections_ip_counts": dict(ip_counts),
                "requests_per_minute": requests_per_minute,
                "total_connections_tracked": len(self._connection_start_times),
            }
        )