"""Bandwidth collector — tracks RX/TX rates and maintains rolling history."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from proxywatch.collectors.base import BaseCollector
from proxywatch.utils.net_parser import read_iface_bytes


class BandwidthCollector(BaseCollector):
    """Collects interface bandwidth rates and maintains a rolling history.

    Reads from /sys/class/net/<iface>/statistics/ every tick, computes
    delta-based Mbps rates, and stores a configurable-length history
    for the ASCII network graph.
    """

    def __init__(
        self,
        data_store: dict[str, Any],
        interface: str = "eth0",
        interval: float = 1.0,
        history_seconds: int = 300,
    ) -> None:
        super().__init__(data_store, interval)
        self.interface = interface
        self._last_rx: int = 0
        self._last_tx: int = 0
        self._last_time: float = 0.0
        self._initialized = False

        self._rx_history: deque[float] = deque(maxlen=history_seconds)
        self._tx_history: deque[float] = deque(maxlen=history_seconds)

        # Accumulated totals (bytes, persisted across sessions)
        self._total_rx: int = 0
        self._total_tx: int = 0

        # Daily tracking
        self._daily_rx: int = 0
        self._daily_tx: int = 0
        self._current_day: str = ""
        self._peak_bps_today: float = 0.0
        self._peak_conns_today: int = 0

    async def collect(self) -> None:
        """Read interface byte counters and compute rates."""
        now = time.time()
        rx, tx = read_iface_bytes(self.interface)

        rx_rate = 0.0
        tx_rate = 0.0

        if self._initialized and self._last_time > 0:
            elapsed = now - self._last_time
            if elapsed > 0:
                rx_delta = max(0, rx - self._last_rx)
                tx_delta = max(0, tx - self._last_tx)
                # Convert bytes/sec to bits/sec (×8)
                rx_rate = (rx_delta / elapsed) * 8
                tx_rate = (tx_delta / elapsed) * 8

                self._total_rx += rx_delta
                self._total_tx += tx_delta
                self._daily_rx += rx_delta
                self._daily_tx += tx_delta

        self._last_rx = rx
        self._last_tx = tx
        self._last_time = now
        self._initialized = True

        self._rx_history.append(rx_rate)
        self._tx_history.append(tx_rate)

        # Daily reset check
        today = time.strftime("%Y-%m-%d")
        if today != self._current_day:
            self._daily_rx = 0
            self._daily_tx = 0
            self._peak_bps_today = 0.0
            self._peak_conns_today = 0
            self._current_day = today

        # Track peak bandwidth today
        peak = max(rx_rate, tx_rate)
        if peak > self._peak_bps_today:
            self._peak_bps_today = peak

        self.data_store.update(
            {
                "bandwidth_rx_bps": rx_rate,
                "bandwidth_tx_bps": tx_rate,
                "bandwidth_rx_history": list(self._rx_history),
                "bandwidth_tx_history": list(self._tx_history),
                "bandwidth_total_rx": self._total_rx,
                "bandwidth_total_tx": self._total_tx,
                "bandwidth_daily_rx": self._daily_rx,
                "bandwidth_daily_tx": self._daily_tx,
                "bandwidth_peak_bps_today": self._peak_bps_today,
                "bandwidth_peak_conns_today": self._peak_conns_today,
            }
        )

    def record_peak_connections(self, count: int) -> None:
        """Update peak connections today if count is higher."""
        if count > self._peak_conns_today:
            self._peak_conns_today = count