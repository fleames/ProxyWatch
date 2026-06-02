"""Security monitor collector — detects anomalies and raises alerts."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from proxywatch.collectors.base import BaseCollector


class SecurityCollector(BaseCollector):
    """Monitors proxy connections for security anomalies.

    Detects:
    - Unknown client IPs connecting
    - Excessive bandwidth usage
    - Connection spikes
    - Container restarts
    - Port no longer listening
    """

    def __init__(
        self,
        data_store: dict[str, Any],
        trusted_clients: list[str],
        alert_thresholds: dict[str, Any],
        interval: float = 1.0,
    ) -> None:
        super().__init__(data_store, interval)
        self.trusted_clients = set(trusted_clients)
        self.thresholds = alert_thresholds
        self._alerts: list[dict[str, Any]] = []
        self._alert_history: set[str] = set()  # Deduplicate alerts
        self._prev_connections: int = 0
        self._prev_container_running: bool | None = None
        self._conn_spike_window: list[int] = []
        self._ip_conn_rates: dict[str, list[float]] = defaultdict(list)
        self._ip_bw: dict[str, float] = defaultdict(float)

    def _add_alert(self, level: str, message: str, category: str) -> None:
        """Add a security alert, deduplicating by message content."""
        alert_key = f"{category}:{message}"
        if alert_key in self._alert_history:
            return
        self._alert_history.add(alert_key)
        # Keep last 100 unique alerts
        if len(self._alert_history) > 100:
            self._alert_history.clear()

        self._alerts.append(
            {
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "category": category,
            }
        )
        # Keep last 50 alerts
        if len(self._alerts) > 50:
            self._alerts = self._alerts[-50:]

    async def collect(self) -> None:
        """Run all security checks."""
        # Clear transient alerts (re-evaluate every tick)
        self._alerts = [a for a in self._alerts if a["category"] == "container_restart"]

        # 1. Check for unknown client IPs
        await self._check_unknown_clients()

        # 2. Check for excessive bandwidth
        await self._check_bandwidth()

        # 3. Check for connection spikes
        await self._check_connection_spikes()

        # 4. Check for container restarts
        await self._check_container_restarts()

        # 5. Check port listening
        await self._check_port_listening()

        self.data_store.update({"security_alerts": list(self._alerts)})

    async def _check_unknown_clients(self) -> None:
        """Detect connections from untrusted IPs."""
        if not self.thresholds.get("unknown_client_alert", True):
            return

        connections = self.data_store.get_sync("connections_details", [])
        seen_ips: set[str] = set()
        for conn in connections:
            src_ip = conn.get("source_ip", "")
            if src_ip and src_ip not in self.trusted_clients and src_ip != "0.0.0.0" and src_ip != "::":
                if src_ip not in seen_ips:
                    seen_ips.add(src_ip)
                    self._add_alert(
                        "warning",
                        f"Unknown client {src_ip} connected",
                        "unknown_client",
                    )

        # Track connection rate per IP for spike detection
        ip_counts: dict[str, int] = defaultdict(int)
        for conn in connections:
            src_ip = conn.get("source_ip", "")
            if src_ip:
                ip_counts[src_ip] += 1

        now = time.time()
        for ip, count in ip_counts.items():
            self._ip_conn_rates[ip].append(now)
            # Keep last 60 seconds
            self._ip_conn_rates[ip] = [t for t in self._ip_conn_rates[ip] if now - t <= 60]

    async def _check_bandwidth(self) -> None:
        """Check for excessive bandwidth usage."""
        threshold_mbps = self.thresholds.get("bandwidth_mbps", 100)
        rx_bps = self.data_store.get_sync("bandwidth_rx_bps", 0.0)
        tx_bps = self.data_store.get_sync("bandwidth_tx_bps", 0.0)

        total_mbps = (rx_bps + tx_bps) / 1_000_000
        if total_mbps > threshold_mbps:
            self._add_alert(
                "warning",
                f"High bandwidth: {total_mbps:.1f} Mbps (threshold: {threshold_mbps} Mbps)",
                "bandwidth_spike",
            )

    async def _check_connection_spikes(self) -> None:
        """Detect sudden spikes in connection count."""
        threshold = self.thresholds.get("connections_per_minute", 50)
        current = self.data_store.get_sync("connections_active", 0)
        delta = current - self._prev_connections
        self._prev_connections = current

        if delta > threshold:
            self._add_alert(
                "warning",
                f"Connection spike: +{delta} connections in 1 second (threshold: {threshold})",
                "connection_spike",
            )

    async def _check_container_restarts(self) -> None:
        """Detect if the proxy container has restarted."""
        if not self.thresholds.get("container_restart_alert", True):
            return

        current_running = self.data_store.get_sync("proxy_container_running", False)

        if self._prev_container_running is True and current_running is False:
            self._add_alert(
                "error",
                "Proxy container has stopped!",
                "container_restart",
            )
        elif self._prev_container_running is False and current_running is True:
            self._add_alert(
                "warning",
                "Proxy container has restarted",
                "container_restart",
            )

        self._prev_container_running = current_running

    async def _check_port_listening(self) -> None:
        """Check if the proxy port is being listened on."""
        if not self.thresholds.get("port_down_alert", True):
            return

        listening = self.data_store.get_sync("connections_listening", 0)
        if listening == 0:
            self._add_alert(
                "error",
                "Proxy port is NOT listening!",
                "port_down",
            )

    def clear_alerts(self) -> None:
        """Clear all security alerts."""
        self._alerts.clear()
        self._alert_history.clear()
        self.data_store.update({"security_alerts": []})