"""Panel 3 — Top Destinations table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, DataTable

from proxywatch.utils.formatting import fmt_bytes


class TopDestinationsPanel(Container):
    """Displays the most contacted destination IPs by connections and bandwidth."""

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._table: DataTable | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]TOP DESTINATIONS[/bold cyan]", id="dest-title")
        yield DataTable(id="dest-table")

    def on_mount(self) -> None:
        self._table = self.query_one("#dest-table", DataTable)
        self._table.add_columns("IP", "Conns", "RX", "TX", "%")
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._table is None:
            return

        destinations = self.data_store.get_sync("top_destinations", [])

        rows: list[tuple] = []
        for d in destinations[:15]:
            ip = d.get("ip", "-")
            conns = str(d.get("connections", 0))
            rx = fmt_bytes(d.get("total_rx", 0))
            tx = fmt_bytes(d.get("total_tx", 0))
            pct = f"{d.get('percentage', 0):.1f}%"
            rows.append((ip, conns, rx, tx, pct))

        # Only clear and re-add if data changed
        current_rows = self._table.row_count
        if current_rows != len(rows) or rows:
            self._table.clear()
            for row in rows:
                self._table.add_row(*row)