"""Panel 5 — ASCII Network Bandwidth Graph with 5-minute rolling history."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from proxywatch.utils.formatting import fmt_bits_per_second


class NetworkGraphPanel(Container):
    """Renders a live ASCII bar chart of incoming/outgoing bandwidth.

    Similar to btop's network graph — uses Unicode block characters
    to draw horizontal bars for RX (blue) and TX (magenta) over a
    rolling window.
    """

    BLOCK_CHARS = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._content: Static | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]NETWORK GRAPH[/bold cyan]", id="graph-title")
        yield Static("Loading...", id="graph-content")

    def on_mount(self) -> None:
        self._content = self.query_one("#graph-content", Static)
        self.set_interval(1, self.refresh_panel)

    @staticmethod
    def _make_bar(value: float, max_val: float, width: int = 40) -> str:
        """Build a horizontal bar string using Unicode block chars."""
        if max_val <= 0:
            fraction = 0.0
        else:
            fraction = min(1.0, value / max_val)

        full_blocks = int(fraction * width)
        remainder = (fraction * width) - full_blocks
        partial_idx = int(remainder * 8)

        bar = "█" * full_blocks
        if partial_idx > 0 and full_blocks < width:
            bar += NetworkGraphPanel.BLOCK_CHARS[partial_idx]

        bar = bar.ljust(width, " ")
        return bar

    def refresh_panel(self) -> None:
        if self._content is None:
            return

        rx_history = self.data_store.get_sync("bandwidth_rx_history", [])
        tx_history = self.data_store.get_sync("bandwidth_tx_history", [])
        rx_current = self.data_store.get_sync("bandwidth_rx_bps", 0.0)
        tx_current = self.data_store.get_sync("bandwidth_tx_bps", 0.0)

        # Determine max for scaling
        all_values = list(rx_history) + list(tx_history) + [rx_current, tx_current]
        max_val = max(all_values) if all_values else 1.0
        if max_val <= 0:
            max_val = 1.0

        # Render time-series bars (compact view)
        lines: list[str] = []
        lines.append(f"  ↓ RX: [blue]{fmt_bits_per_second(rx_current)}[/blue]")
        lines.append(f"  ↑ TX: [magenta]{fmt_bits_per_second(tx_current)}[/magenta]")
        lines.append("")

        graph_width = 50

        # RX bar
        rx_bar = self._make_bar(rx_current, max_val, graph_width)
        lines.append(f"  RX [blue]│{rx_bar}│[/blue]")

        # TX bar
        tx_bar = self._make_bar(tx_current, max_val, graph_width)
        lines.append(f"  TX [magenta]│{tx_bar}│[/magenta]")

        lines.append("")
        lines.append(f"  [dim]Scale: 0 ──── {fmt_bits_per_second(max_val)}[/dim]")
        lines.append(f"  [dim]Window: {len(rx_history)}s / 300s[/dim]")

        self._content.update("\n".join(lines))