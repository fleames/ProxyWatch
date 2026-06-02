"""System metrics collector — hostname, uptime, CPU, RAM, Disk."""

from __future__ import annotations

import os
import time
from typing import Any

import psutil

from proxywatch.collectors.base import BaseCollector


class SystemCollector(BaseCollector):
    """Collects host system metrics using psutil."""

    def __init__(self, data_store: dict[str, Any], interval: float = 1.0) -> None:
        super().__init__(data_store, interval)
        self._boot_time = psutil.boot_time()

    async def collect(self) -> None:
        """Gather system metrics and write to data store."""
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

        hostname = os.uname().nodename

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        self.data_store.update(
            {
                "system_hostname": hostname,
                "system_time": now,
                "system_uptime": uptime_seconds,
                "system_cpu": cpu_percent,
                "system_ram": ram_percent,
                "system_disk": disk_percent,
            }
        )