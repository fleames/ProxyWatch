"""Main ProxyWatch Textual application — dashboard layout, hotkeys, and lifecycle."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Static

from proxywatch.collectors.base import DataStore
from proxywatch.collectors.system import SystemCollector
from proxywatch.collectors.docker_collector import DockerCollector
from proxywatch.collectors.connections import ConnectionCollector
from proxywatch.collectors.bandwidth import BandwidthCollector
from proxywatch.collectors.proxy_stats import ProxyStatsCollector
from proxywatch.collectors.destinations import DestinationsCollector
from proxywatch.collectors.proxy_logs import ProxyLogsCollector
from proxywatch.collectors.security import SecurityCollector
from proxywatch.config import load_config, validate_config
from proxywatch.exporters.json_exporter import export_json
from proxywatch.exporters.csv_exporter import export_csv
from proxywatch.splash import SplashScreen
from proxywatch.widgets.header import DashboardHeader
from proxywatch.widgets.proxy_status import ProxyStatusPanel
from proxywatch.widgets.client_connections import ClientConnectionsPanel
from proxywatch.widgets.top_destinations import TopDestinationsPanel
from proxywatch.widgets.proxy_logs import ProxyLogsPanel
from proxywatch.widgets.network_graph import NetworkGraphPanel
from proxywatch.widgets.trusted_clients import TrustedClientsPanel
from proxywatch.widgets.docker_health import DockerHealthPanel
from proxywatch.widgets.security_alerts import SecurityAlertsPanel


class ProxyWatchApp(App):
    """Main dashboard application."""

    CSS = """
    Screen {
        background: #0a0a1a;
    }

    #header-bar {
        dock: top;
        height: 1;
        background: #1a1a3a;
        padding: 0 1;
        text-style: bold;
    }

    #main-grid {
        layout: grid;
        grid-size: 3;
        grid-rows: auto;
        grid-gutter: 0 1;
        padding: 1;
    }

    #top-row {
        layout: grid;
        grid-size: 3;
        grid-rows: auto;
        grid-gutter: 0 1;
        height: auto;
        margin-bottom: 1;
    }

    #middle-row {
        layout: grid;
        grid-size: 1;
        grid-rows: auto;
        height: auto;
        margin-bottom: 1;
    }

    #bottom-row {
        layout: grid;
        grid-size: 3;
        grid-rows: auto;
        grid-gutter: 0 1;
        height: auto;
        margin-bottom: 1;
    }

    #security-row {
        layout: grid;
        grid-size: 1;
        grid-rows: auto;
        height: auto;
    }

    .panel {
        border: solid #3333aa;
        background: #0d0d2d;
        padding: 1 1;
        height: auto;
        min-height: 10;
    }

    .panel-title {
        text-style: bold;
        color: #00aaaa;
        background: #1a1a4a;
        padding: 0 1;
    }

    #logs-row {
        height: auto;
        min-height: 10;
        max-height: 15;
    }

    #security-row {
        height: auto;
        max-height: 8;
    }

    Footer {
        background: #1a1a3a;
        color: #888888;
    }

    DataTable {
        background: #0d0d2d;
    }

    RichLog {
        background: #0d0d2d;
        overflow-y: scroll;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("l", "clear_logs", "Clear Logs"),
        ("d", "toggle_docker", "Docker Panel"),
        ("n", "toggle_network", "Network Graph"),
        ("s", "toggle_security", "Security Panel"),
        ("ctrl+e", "export_metrics", "Export Metrics"),
    ]

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__()
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.data_store = DataStore()
        self._collectors: list[Any] = []
        self._docker_visible = True
        self._network_visible = True
        self._security_visible = True
        self._log_collector: ProxyLogsCollector | None = None

    def on_mount(self) -> None:
        """Setup config, collectors, and show splash."""
        # Load config
        self.config = load_config(self.config_path)
        validate_config(self.config)

        # Show splash screen
        self.push_screen(SplashScreen())

        # Start collectors and timed tasks
        self.set_timer(0.5, self._start_collectors)
        self.set_interval(self.config.get("refresh_rate", 1), self._export_tick)

    async def _start_collectors(self) -> None:
        """Initialize and start all data collectors."""
        trusted = self.config.get("trusted_clients", [])
        proxy_container = self.config.get("proxy_container", "socks5")
        proxy_port = self.config.get("proxy_port", 1081)
        net_iface = self.config.get("network_interface", "eth0")
        interval = self.config.get("refresh_rate", 1)
        graph_secs = self.config.get("graph_history_seconds", 300)
        log_lines = self.config.get("log_lines", 50)
        alert_cfg = self.config.get("alert_thresholds", {})

        # System
        sys_col = SystemCollector(self.data_store, interval)
        await sys_col.start()
        self._collectors.append(sys_col)

        # Docker (socks5 + wg-easy)
        docker_col = DockerCollector(
            self.data_store,
            [proxy_container, "wg-easy"],
            interval,
        )
        await docker_col.start()
        self._collectors.append(docker_col)

        # Connections
        conn_col = ConnectionCollector(self.data_store, proxy_port, interval)
        await conn_col.start()
        self._collectors.append(conn_col)

        # Bandwidth
        bw_col = BandwidthCollector(self.data_store, net_iface, interval, graph_secs)
        await bw_col.start()
        self._collectors.append(bw_col)

        # Proxy stats (aggregator)
        stats_col = ProxyStatsCollector(self.data_store, interval)
        await stats_col.start()
        self._collectors.append(stats_col)

        # Destinations
        dest_col = DestinationsCollector(self.data_store, interval)
        await dest_col.start()
        self._collectors.append(dest_col)

        # Logs
        self._log_collector = ProxyLogsCollector(
            self.data_store, proxy_container, log_lines, interval
        )
        await self._log_collector.start()
        self._collectors.append(self._log_collector)

        # Security
        sec_col = SecurityCollector(self.data_store, trusted, alert_cfg, interval)
        await sec_col.start()
        self._collectors.append(sec_col)

    async def _export_tick(self) -> None:
        """Periodic export of metrics to JSON and CSV."""
        export_cfg = self.config.get("export", {})
        json_path = export_cfg.get("json_path", "/tmp/proxywatch_metrics.json")
        csv_path = export_cfg.get("csv_path", "/tmp/proxywatch_metrics.csv")

        try:
            await asyncio.to_thread(export_json, self.data_store, json_path)
        except Exception:
            pass

        try:
            await asyncio.to_thread(export_csv, self.data_store, csv_path)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        """Build the dashboard layout."""
        # Header
        yield DashboardHeader(self.data_store)

        # Top row: Proxy Status | Live Connections | Top Destinations
        with Container(id="top-row"):
            with Container(classes="panel"):
                yield ProxyStatusPanel(self.data_store)
            with Container(classes="panel"):
                yield ClientConnectionsPanel(self.data_store)
            with Container(classes="panel"):
                yield TopDestinationsPanel(self.data_store)

        # Middle row: Proxy Logs (full width)
        with Container(id="middle-row"):
            with Container(classes="panel", id="logs-row"):
                yield ProxyLogsPanel(self.data_store)

        # Bottom row: Network Graph | Trusted Clients | Docker Health
        with Container(id="bottom-row"):
            with Container(classes="panel", id="network-panel"):
                yield NetworkGraphPanel(self.data_store)
            with Container(classes="panel"):
                yield TrustedClientsPanel(
                    self.data_store,
                    self.config.get("trusted_clients", []),
                )
            with Container(classes="panel", id="docker-panel"):
                yield DockerHealthPanel(self.data_store)

        # Security row (full width)
        with Container(id="security-row"):
            with Container(classes="panel", id="security-panel"):
                yield SecurityAlertsPanel(self.data_store)

        # Footer with hotkeys
        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Force refresh all panels."""
        pass  # All panels auto-refresh via set_interval

    def action_clear_logs(self) -> None:
        """Clear the proxy log panel."""
        if self._log_collector:
            self._log_collector.clear_logs()

    def action_toggle_docker(self) -> None:
        """Toggle Docker health panel visibility."""
        self._docker_visible = not self._docker_visible
        panel = self.query_one("#docker-panel", Container)
        panel.display = "block" if self._docker_visible else "none"

    def action_toggle_network(self) -> None:
        """Toggle network graph panel visibility."""
        self._network_visible = not self._network_visible
        panel = self.query_one("#network-panel", Container)
        panel.display = "block" if self._network_visible else "none"

    def action_toggle_security(self) -> None:
        """Toggle security alerts panel visibility."""
        self._security_visible = not self._security_visible
        panel = self.query_one("#security-panel", Container)
        panel.display = "block" if self._security_visible else "none"

    def action_export_metrics(self) -> None:
        """Perform immediate metrics export."""
        export_cfg = self.config.get("export", {})
        json_path = export_cfg.get("json_path", "/tmp/proxywatch_metrics.json")
        csv_path = export_cfg.get("csv_path", "/tmp/proxywatch_metrics.csv")

        try:
            export_json(self.data_store, json_path)
            self.notify(f"Metrics exported to {json_path}", title="Export")
        except Exception as e:
            self.notify(f"Export failed: {e}", title="Error", severity="error")

        try:
            export_csv(self.data_store, csv_path)
        except Exception:
            pass

    async def on_unmount(self) -> None:
        """Stop all collectors on exit."""
        for collector in self._collectors:
            try:
                await collector.stop()
            except Exception:
                pass