"""Panel 8 — Security Alerts panel."""

from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from proxywatch.utils.formatting import fmt_duration


class SecurityAlertsPanel(Container):
    """Displays security alerts with timestamp and severity colors.

    Alerts are categorized:
    - error (red): Container stopped, port down
    - warning (yellow): Unknown client, bandwidth spike, connection spike
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._content: Static | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]SECURITY ALERTS[/bold cyan]", id="security-title")
        yield Static("No alerts", id="security-content")

    def on_mount(self) -> None:
        self._content = self.query_one("#security-content", Static)
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        if self._content is None:
            return

        alerts = self.data_store.get_sync("security_alerts", [])

        if not alerts:
            self._content.update("[green]✓ No alerts[/green]")
            return

        now = time.time()
        lines: list[str] = []

        for alert in alerts[-20:]:  # Show last 20
            level = alert.get("level", "info")
            message = alert.get("message", "")
            ts = alert.get("timestamp", now)
            ago = fmt_duration(int(now - ts))

            prefix = {
                "error": "[bold red]ERR[/bold red]",
                "warning": "[bold yellow]WARN[/bold yellow]",
                "info": "[green]INFO[/green]",
            }.get(level, "[white]INFO[/white]")

            lines.append(f"  {prefix} [dim]{ago} ago[/dim] {message}")

        self._content.update("\n".join(lines))