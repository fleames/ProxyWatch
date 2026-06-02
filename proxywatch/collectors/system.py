"""System metrics collector — hostname, uptime, CPU, RAM, Disk (local + remote)."""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from proxywatch.collectors.base import BaseCollector

if TYPE_CHECKING:
    from proxywatch.remote import RemoteClient


class SystemCollector(BaseCollector):
    """Collects host system metrics — locally or over SSH."""

    def __init__(
        self,
        data_store: dict[str, Any],
        interval: float = 1.0,
        remote_client: "RemoteClient | None" = None,
    ) -> None:
        super().__init__(data_store, interval)
        self._remote = remote_client
        self._boot_time: float = 0.0
        self._boot_time_set = False

    async def _collect_local(self) -> None:
        """Gather system metrics via psutil (local mode)."""
        import psutil
        import os as _os

        if not self._boot_time_set:
            try:
                self._boot_time = psutil.boot_time()
                self._boot_time_set = True
            except Exception:
                self._boot_time = time.time()
                self._boot_time_set = True

        try:
            cpu_percent = psutil.cpu_percent(interval=None) / 100.0
        except Exception:
            cpu_percent = 0.0

        try:
            mem = psutil.virtual_memory()
            ram_percent = mem.percent / 100.0
        except Exception:
            ram_percent = 0.0

        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent / 100.0
        except Exception:
            disk_percent = 0.0

        uptime_seconds = int(time.time() - self._boot_time)
        hostname = _os.uname().nodename
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        self.data_store.update({
            "system_hostname": hostname,
            "system_time": now,
            "system_uptime": uptime_seconds,
            "system_cpu": cpu_percent,
            "system_ram": ram_percent,
            "system_disk": disk_percent,
        })

    async def _collect_remote(self) -> None:
        """Gather system metrics via SSH commands."""
        if self._remote is None:
            return

        connected = await self._remote.ensure_connected()
        if not connected:
            self.data_store.update({
                "system_hostname": self._remote.host,
                "system_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "system_uptime": 0,
                "system_cpu": 0.0,
                "system_ram": 0.0,
                "system_disk": 0.0,
                "remote_connected": False,
                "remote_error": self._remote.last_error,
            })
            return

        commands = {
            "hostname": "hostname",
            "uptime": "cat /proc/uptime",
            "cpu": "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",  # user CPU%
            "ram": "free -m | grep Mem | awk '{print $3,$2}'",  # used, total MB
            "disk": "df / | tail -1 | awk '{print $5}'",
        }

        results = await self._remote.run_many(commands, timeout=10.0)

        # Parse hostname
        hostname = results["hostname"]["stdout"] or self._remote.host

        # Parse uptime
        uptime_seconds = 0
        uptime_raw = results["uptime"]["stdout"]
        if uptime_raw:
            try:
                uptime_seconds = int(float(uptime_raw.split()[0]))
            except (ValueError, IndexError):
                pass

        # Parse CPU
        cpu_percent = 0.0
        cpu_raw = results["cpu"]["stdout"]
        if cpu_raw:
            try:
                cpu_percent = float(cpu_raw) / 100.0
            except ValueError:
                pass

        # Parse RAM
        ram_percent = 0.0
        ram_raw = results["ram"]["stdout"]
        if ram_raw:
            try:
                parts = ram_raw.split()
                if len(parts) >= 2:
                    used = float(parts[0])
                    total = float(parts[1])
                    if total > 0:
                        ram_percent = used / total
            except (ValueError, IndexError):
                pass

        # Parse Disk
        disk_percent = 0.0
        disk_raw = results["disk"]["stdout"]
        if disk_raw:
            try:
                disk_percent = float(disk_raw.replace("%", "")) / 100.0
            except ValueError:
                pass

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        self.data_store.update({
            "system_hostname": hostname,
            "system_time": now,
            "system_uptime": uptime_seconds,
            "system_cpu": cpu_percent,
            "system_ram": ram_percent,
            "system_disk": disk_percent,
            "remote_connected": True,
            "remote_error": "",
        })

    async def collect(self) -> None:
        """Gather system metrics and write to data store."""
        if self._remote:
            await self._collect_remote()
        else:
            await self._collect_local()