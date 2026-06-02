"""Panel 4 — Recent Proxy Logs with color-coded levels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, RichLog


class ProxyLogsPanel(Container):
    """Displays the last N log lines from the proxy container.

    Color-coding:
    - INFO → green
    - WARN → yellow
    - ERR/ERROR → red
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._log_widget: RichLog | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]PROXY LOGS[/bold cyan]", id="logs-title")
        yield RichLog(id="logs-view", highlight=True, markup=True, max_lines=100)

    def on_mount(self) -> None:
        self._log_widget = self.query_one("#logs-view", RichLog)
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._log_widget is None:
            return

        logs = self.data_store.get_sync("proxy_logs", [])
        if not logs:
            return

        # Instead of clearing all the time, we just check if new lines appeared
        # by tracking the count
        current_count = getattr(self, "_last_log_count", 0)
        if len(logs) == current_count:
            return

        self._last_log_count = len(logs)

        # Clear and rewrite (RichLog doesn't have a great diff mechanism)
        self._log_widget.clear()

        for entry in logs[-50:]:
            text = entry.get("text", "")
            level = entry.get("level", "info")

            if level == "error":
                self._log_widget.write(f"[red]{text}[/red]")
            elif level == "warning":
                self._log_widget.write(f"[yellow]{text}[/yellow]")
            else:
                self._log_widget.write(f"[green]{text}[/green]")

    def clear(self) -> None:
        """Clear the log display."""
        if self._log_widget:
            self._log_widget.clear()
        self._last_log_count = 0