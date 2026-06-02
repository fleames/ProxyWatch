"""Top destinations collector — tracks most contacted destination IPs."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from proxywatch.collectors.base import BaseCollector


class DestinationsCollector(BaseCollector):
    """Aggregates destination statistics from active connections.

    Maintains per-destination connection counts and cumulative bandwidth.
    """

    def __init__(self, data_store: dict[str, Any], interval: float = 1.0) -> None:
        super().__init__(data_store, interval)
        self._dest_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"connections": 0, "total_rx": 0, "total_tx": 0, "last_seen": 0.0}
        )
        self._prev_rx_total: int = 0
        self._prev_tx_total: int = 0
        self._last_tick: float = 0.0

    async def collect(self) -> None:
        """Aggregate per-destination statistics from connection data."""
        now = time.time()
        connections = self.data_store.get_sync("connections_details", [])

        # Get current total bandwidth
        total_rx = self.data_store.get_sync("bandwidth_total_rx", 0)
        total_tx = self.data_store.get_sync("bandwidth_total_tx", 0)

        # Calculate delta since last tick
        rx_delta = 0
        tx_delta = 0
        if self._last_tick > 0:
            rx_delta = max(0, total_rx - self._prev_rx_total)
            tx_delta = max(0, total_tx - self._prev_tx_total)

        self._prev_rx_total = total_rx
        self._prev_tx_total = total_tx
        self._last_tick = now

        # Track which destinations are currently active
        active_dests: set[str] = set()

        for conn in connections:
            dest_ip = conn.get("destination_ip", "unknown")
            active_dests.add(dest_ip)

            stats = self._dest_stats[dest_ip]
            stats["last_seen"] = now

            # Increment rough bandwidth allocation (divided among connections to this dest)
            # More accurate would be per-connection, but proc doesn't expose per-socket counters easily
            if dest_ip not in active_dests or len(active_dests) == 1:
                pass  # We'll distribute delta bandwidth below

        # Distribute delta bandwidth across active destinations proportionally
        num_active = len(active_dests)
        if num_active > 0 and (rx_delta > 0 or tx_delta > 0):
            rx_share = rx_delta // num_active
            tx_share = tx_delta // num_active
            for dest_ip in active_dests:
                self._dest_stats[dest_ip]["total_rx"] += rx_share
                self._dest_stats[dest_ip]["total_tx"] += tx_share

        # Count current connections per destination
        # Reset connection counts
        for key in self._dest_stats:
            self._dest_stats[key]["connections"] = 0

        for conn in connections:
            dest_ip = conn.get("destination_ip", "unknown")
            self._dest_stats[dest_ip]["connections"] += 1

        # Build sorted list
        dest_list: list[dict[str, Any]] = []
        for ip, stats in self._dest_stats.items():
            if stats["connections"] > 0 or (now - stats["last_seen"]) < 60:
                dest_list.append(
                    {
                        "ip": ip,
                        "connections": stats["connections"],
                        "total_rx": stats["total_rx"],
                        "total_tx": stats["total_tx"],
                    }
                )

        # Sort by total bandwidth (RX + TX), descending
        dest_list.sort(key=lambda d: d["total_rx"] + d["total_tx"], reverse=True)

        # Calculate percentages for top 10
        total_all_bandwidth = sum(d["total_rx"] + d["total_tx"] for d in dest_list)
        for d in dest_list[:20]:
            bw = d["total_rx"] + d["total_tx"]
            d["percentage"] = (bw / total_all_bandwidth * 100) if total_all_bandwidth > 0 else 0.0

        self.data_store.update({"top_destinations": dest_list[:20]})