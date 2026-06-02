"""Panel 6 — Trusted Client Statistics table."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, DataTable

from proxywatch.utils.formatting import fmt_bytes


class TrustedClientsPanel(Container):
    """Displays per-client usage statistics sorted by bandwidth.

    Tracks connections, RX, and TX for trusted clients only.
    """

    def __init__(self, data_store, trusted_clients: list[str]) -> None:
        super().__init__()
        self.data_store = data_store
        self.trusted_clients = set(trusted_clients)
        self._table: DataTable | None = None

        # Persistent accumulator for per-client totals
        self._client_totals: dict[str, dict[str, int]] = defaultdict(
            lambda: {"connections": 0, "rx": 0, "tx": 0}
        )
        self._prev_conn_details: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]TRUSTED CLIENT STATS[/bold cyan]", id="trusted-title")
        yield DataTable(id="trusted-table")

    def on_mount(self) -> None:
        self._table = self.query_one("#trusted-table", DataTable)
        self._table.add_columns("Client", "Connections", "RX", "TX")
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._table is None:
            return

        connections = self.data_store.get_sync("connections_details", [])
        total_rx = self.data_store.get_sync("bandwidth_total_rx", 0)
        total_tx = self.data_store.get_sync("bandwidth_total_tx", 0)

        # Count current connections per trusted client
        current_counts: dict[str, int] = defaultdict(int)
        for conn in connections:
            src_ip = conn.get("source_ip", "")
            if src_ip in self.trusted_clients:
                current_counts[src_ip] += 1
                # Accumulate connection count
                self._client_totals[src_ip]["connections"] += 1

        # Distribute bandwidth proportionally among active trusted clients
        active_trusted = [ip for ip, count in current_counts.items() if count > 0]
        num_active = len(active_trusted)

        # Get bandwidth delta since last tick
        prev_rx = self.data_store.get_sync("_prev_trusted_total_rx", 0)
        prev_tx = self.data_store.get_sync("_prev_trusted_total_tx", 0)
        rx_delta = max(0, total_rx - prev_rx)
        tx_delta = max(0, total_tx - prev_tx)
        self.data_store.update({"_prev_trusted_total_rx": total_rx, "_prev_trusted_total_tx": total_tx})

        if num_active > 0 and (rx_delta > 0 or tx_delta > 0):
            rx_share = rx_delta // num_active
            tx_share = tx_delta // num_active
            for ip in active_trusted:
                self._client_totals[ip]["rx"] += rx_share
                self._client_totals[ip]["tx"] += tx_share

        # Build rows sorted by total bandwidth
        client_list: list[tuple[str, dict[str, int]]] = []
        for ip, stats in self._client_totals.items():
            client_list.append((ip, stats))

        client_list.sort(key=lambda x: x[1]["rx"] + x[1]["tx"], reverse=True)

        rows = []
        for ip, stats in client_list:
            conns = str(stats["connections"])
            rx = fmt_bytes(stats["rx"])
            tx = fmt_bytes(stats["tx"])
            rows.append((ip, conns, rx, tx))

        self._table.clear()
        for row in rows:
            self._table.add_row(*row)