"""Panel 1 — SOCKS5 Proxy Status card."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from proxywatch.utils.formatting import (
    fmt_bits_per_second,
    fmt_bytes,
    fmt_duration,
    fmt_number,
)


class ProxyStatusPanel(Container):
    """Displays proxy container status, uptime, connections, bandwidth, totals."""

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._content = Static("Loading...", id="proxy-status-content")

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]SOCKS5 STATUS[/bold cyan]", id="proxy-status-title")
        yield self._content

    def on_mount(self) -> None:
        self.set_interval(1, self.refresh_panel)

    def refresh_panel(self) -> None:
        online = self.data_store.get_sync("proxy_online", False)
        uptime = self.data_store.get_sync("proxy_uptime", 0)
        active = self.data_store.get_sync("connections_active", 0)
        rpm = self.data_store.get_sync("requests_per_minute", 0)
        rx_bps = self.data_store.get_sync("bandwidth_rx_bps", 0.0)
        tx_bps = self.data_store.get_sync("bandwidth_tx_bps", 0.0)
        total_rx = self.data_store.get_sync("bandwidth_total_rx", 0)
        total_tx = self.data_store.get_sync("bandwidth_total_tx", 0)
        daily_rx = self.data_store.get_sync("bandwidth_daily_rx", 0)
        daily_tx = self.data_store.get_sync("bandwidth_daily_tx", 0)
        peak_bps = self.data_store.get_sync("bandwidth_peak_bps_today", 0.0)
        peak_conns = self.data_store.get_sync("bandwidth_peak_conns_today", 0)

        status_color = "[bold green]" if online else "[bold red]"
        status_text = "ONLINE" if online else "OFFLINE"

        lines = [
            f"",
            f"  Status:    {status_color}{status_text}[/]",
            f"  Uptime:    [white]{fmt_duration(uptime)}[/]",
            f"  Active:    [yellow]{fmt_number(active)}[/]",
            f"  Req/min:   [yellow]{fmt_number(rpm)}[/]",
            f"",
            f"  Bandwidth:",
            f"    ↓ [blue]{fmt_bits_per_second(rx_bps)}[/]",
            f"    ↑ [magenta]{fmt_bits_per_second(tx_bps)}[/]",
            f"",
            f"  Total:",
            f"    RX [blue]{fmt_bytes(total_rx)}[/]",
            f"    TX [magenta]{fmt_bytes(total_tx)}[/]",
            f"",
            f"  Today:",
            f"    RX [blue]{fmt_bytes(daily_rx)}[/]",
            f"    TX [magenta]{fmt_bytes(daily_tx)}[/]",
            f"    Peak [yellow]{fmt_bits_per_second(peak_bps)}[/]",
            f"    Peak Conns [yellow]{peak_conns}[/]",
        ]

        self._content.update("\n".join(lines))