"""Top header bar displaying hostname, time, uptime, CPU, RAM, Disk."""

from __future__ import annotations

import time
from collections import deque

from textual.app import ComposeResult
from textual.widgets import Header, Static

from proxywatch.utils.formatting import (
    fmt_percentage,
    fmt_uptime,
)


class DashboardHeader(Static):
    """Custom header bar that auto-refreshes from the data store.

    Displays: HOSTNAME | TIME | UPTIME | CPU% | RAM% | DISK%
    """

    def __init__(self, data_store) -> None:
        super().__init__("")
        self.data_store = data_store

    def on_mount(self) -> None:
        self.set_interval(1, self.update_header)

    def update_header(self) -> None:
        """Refresh the header display every second."""
        hostname = self.data_store.get_sync("system_hostname", "unknown")
        sys_time = self.data_store.get_sync("system_time", time.strftime("%Y-%m-%d %H:%M:%S"))
        uptime = self.data_store.get_sync("system_uptime", 0)
        cpu = self.data_store.get_sync("system_cpu", 0.0)
        ram = self.data_store.get_sync("system_ram", 0.0)
        disk = self.data_store.get_sync("system_disk", 0.0)

        cpu_str = fmt_percentage(cpu)
        ram_str = fmt_percentage(ram)
        disk_str = fmt_percentage(disk)
        uptime_str = fmt_uptime(uptime)

        self.update(
            f" [bold cyan]{hostname}[/bold cyan] │ "
            f"[white]{sys_time}[/white] │ "
            f"[green]UP {uptime_str}[/green] │ "
            f"[yellow]CPU {cpu_str}[/yellow] │ "
            f"[magenta]RAM {ram_str}[/magenta] │ "
            f"[blue]DISK {disk_str}[/blue]"
        )