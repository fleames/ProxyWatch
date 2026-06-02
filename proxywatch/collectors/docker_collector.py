"""Docker container health collector for socks5 and wg-easy."""

from __future__ import annotations

import asyncio
from typing import Any

from proxywatch.collectors.base import BaseCollector


class DockerCollector(BaseCollector):
    """Collects container status, CPU%, memory usage, and network I/O.

    Uses the Docker SDK via asyncio.to_thread() to avoid blocking the event loop.
    """

    def __init__(
        self,
        data_store: dict[str, Any],
        container_names: list[str],
        interval: float = 1.0,
    ) -> None:
        super().__init__(data_store, interval)
        self.container_names = container_names
        self._client = None
        self._docker_available = False

    def _get_client(self):
        """Lazy-load docker client."""
        if self._client is None:
            try:
                import docker

                self._client = docker.from_env()
                self._docker_available = True
            except Exception:
                self._docker_available = False
                self._client = None
        return self._client

    def _collect_sync(self) -> dict[str, Any]:
        """Synchronous collection logic — runs in thread pool."""
        result: dict[str, Any] = {
            "docker_containers": [],
            "proxy_container_running": False,
            "proxy_container_started_at": None,
        }

        client = self._get_client()
        if client is None:
            return result

        try:
            for name in self.container_names:
                try:
                    container = client.containers.get(name)
                except Exception:
                    result["docker_containers"].append(
                        {
                            "name": name,
                            "status": "NOT FOUND",
                            "cpu_percent": 0.0,
                            "mem_mb": 0.0,
                            "net_rx": 0,
                            "net_tx": 0,
                            "running": False,
                        }
                    )
                    continue

                stats = None
                mem_mb = 0.0
                cpu_pct = 0.0
                net_rx = 0
                net_tx = 0

                try:
                    # Get a single stats snapshot
                    stats_stream = container.stats(stream=False)
                    if stats_stream:
                        stats = stats_stream

                        # CPU calculation
                        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        system_delta = stats["cpu_stats"].get("system_cpu_usage", 0) - stats["precpu_stats"].get("system_cpu_usage", 0)
                        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
                        if system_delta > 0 and cpu_delta > 0:
                            cpu_pct = (cpu_delta / system_delta) * num_cpus * 100.0

                        # Memory
                        mem_usage = stats["memory_stats"].get("usage", 0)
                        mem_mb = mem_usage / (1024 * 1024)

                        # Network
                        networks = stats.get("networks", {})
                        for iface_stats in networks.values():
                            net_rx += iface_stats.get("rx_bytes", 0)
                            net_tx += iface_stats.get("tx_bytes", 0)
                except Exception:
                    pass

                running = container.status == "running"

                container_info = {
                    "name": name,
                    "status": container.status.upper(),
                    "cpu_percent": round(cpu_pct, 1),
                    "mem_mb": round(mem_mb, 1),
                    "net_rx": net_rx,
                    "net_tx": net_tx,
                    "running": running,
                }
                result["docker_containers"].append(container_info)

                if name == "socks5" and running:
                    result["proxy_container_running"] = True
                    try:
                        attrs = container.attrs
                        started = attrs.get("State", {}).get("StartedAt", "")
                        if started:
                            from datetime import datetime, timezone

                            dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                            result["proxy_container_started_at"] = dt.timestamp()
                    except Exception:
                        pass
        except Exception:
            pass

        return result

    async def collect(self) -> None:
        """Collect docker container health asynchronously."""
        result = await asyncio.to_thread(self._collect_sync)
        self.data_store.update(result)