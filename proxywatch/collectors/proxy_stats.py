"""Proxy statistics aggregator — combines data from other collectors."""

from __future__ import annotations

from typing import Any

from proxywatch.collectors.base import BaseCollector


class ProxyStatsCollector(BaseCollector):
    """Aggregates and derives proxy-level statistics from the shared data store.

    This collector reads values written by ConnectionCollector, BandwidthCollector,
    and DockerCollector, and produces composite metrics like requests/min,
    total connections, and uptime.
    """

    def __init__(self, data_store: dict[str, Any], interval: float = 1.0) -> None:
        super().__init__(data_store, interval)

    async def collect(self) -> None:
        """Derive proxy-wide statistics from current data store state."""
        # This collector primarily acts as a pass-through / aggregator.
        # The key metrics are already computed by their respective collectors.
        # We ensure the data store has consistent keys for the proxy status panel.

        proxy_running = self.data_store.get_sync("proxy_container_running", False)
        started_at = self.data_store.get_sync("proxy_container_started_at")

        import time

        uptime = 0
        if started_at and proxy_running:
            uptime = max(0, int(time.time() - float(started_at)))

        self.data_store.update(
            {
                "proxy_uptime": uptime,
                "proxy_online": proxy_running,
            }
        )