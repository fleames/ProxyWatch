"""Panel 7 — Docker Container Health table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, DataTable

from proxywatch.utils.formatting import fmt_bytes


class DockerHealthPanel(Container):
    """Displays container health for socks5 and wg-easy."""

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._table: DataTable | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]DOCKER HEALTH[/bold cyan]", id="docker-title")
        yield DataTable(id="docker-table")

    def on_mount(self) -> None:
        self._table = self.query_one("#docker-table", DataTable)
        self._table.add_columns("Container", "Status", "CPU%", "Memory", "Net RX", "Net TX")
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._table is None:
            return

        containers = self.data_store.get_sync("docker_containers", [])

        rows: list[tuple] = []
        for c in containers:
            name = c.get("name", "-")
            status = c.get("status", "UNKNOWN")
            cpu = f"{c.get('cpu_percent', 0):.1f}%"
            mem = f"{c.get('mem_mb', 0):.1f} MB"
            net_rx = fmt_bytes(c.get("net_rx", 0))
            net_tx = fmt_bytes(c.get("net_tx", 0))

            # Colorize status
            if c.get("running"):
                status_display = f"[green]{status}[/green]"
            else:
                status_display = f"[red]{status}[/red]"

            rows.append((name, status_display, cpu, mem, net_rx, net_tx))

        if rows:
            self._table.clear()
            for row in rows:
                self._table.add_row(*row)