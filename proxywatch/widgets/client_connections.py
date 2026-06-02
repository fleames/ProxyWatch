"""Panel 2 — Live Client Connections table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, DataTable

from proxywatch.utils.formatting import fmt_duration_short, fmt_bytes


class ClientConnectionsPanel(Container):
    """Displays active client connections in a DataTable."""

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._table: DataTable | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]LIVE CONNECTIONS[/bold cyan]", id="connections-title")
        yield DataTable(id="connections-table")

    def on_mount(self) -> None:
        self._table = self.query_one("#connections-table", DataTable)
        self._table.add_columns("Source IP", "Dest IP", "Port", "Duration", "TX", "RX")
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._table is None:
            return

        connections = self.data_store.get_sync("connections_details", [])

        rows: list[tuple] = []
        for conn in connections[:50]:  # Limit to 50 rows for performance
            source_ip = conn.get("source_ip", "-")
            dest_ip = conn.get("destination_ip", "-")
            dest_port = conn.get("destination_port", "-")
            duration = fmt_duration_short(int(conn.get("duration", 0)))
            tx = fmt_bytes(int(conn.get("tx_queue", 0)))
            rx = fmt_bytes(int(conn.get("rx_queue", 0)))
            rows.append((source_ip, dest_ip, str(dest_port), duration, tx, rx))

        # Only clear and re-add if data changed
        current_rows = self._table.row_count
        if current_rows != len(rows) or rows:
            self._table.clear()
            for row in rows:
                self._table.add_row(*row)