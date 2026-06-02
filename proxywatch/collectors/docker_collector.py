"""Docker container health collector — local Docker SDK or remote SSH docker CLI."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TYPE_CHECKING

from proxywatch.collectors.base import BaseCollector

if TYPE_CHECKING:
    from proxywatch.remote import RemoteClient


class DockerCollector(BaseCollector):
    """Collects container status, CPU%, memory usage, and network I/O."""

    def __init__(
        self,
        data_store: dict[str, Any],
        container_names: list[str],
        interval: float = 1.0,
        remote_client: "RemoteClient | None" = None,
    ) -> None:
        super().__init__(data_store, interval)
        self.container_names = container_names
        self._remote = remote_client
        self._docker_available = False

    async def _collect_local(self) -> dict[str, Any]:
        """Collect via Docker SDK (local mode)."""
        result: dict[str, Any] = {
            "docker_containers": [],
            "proxy_container_running": False,
            "proxy_container_started_at": None,
        }

        try:
            import docker

            client = docker.from_env()
        except Exception:
            return result

        for name in self.container_names:
            try:
                container = client.containers.get(name)
            except Exception:
                result["docker_containers"].append({
                    "name": name,
                    "status": "NOT FOUND",
                    "cpu_percent": 0.0,
                    "mem_mb": 0.0,
                    "net_rx": 0,
                    "net_tx": 0,
                    "running": False,
                })
                continue

            stats = None
            mem_mb = 0.0
            cpu_pct = 0.0
            net_rx = 0
            net_tx = 0

            try:
                stats_stream = container.stats(stream=False)
                if stats_stream:
                    stats = stats_stream
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    system_delta = stats["cpu_stats"].get("system_cpu_usage", 0) - stats["precpu_stats"].get("system_cpu_usage", 0)
                    num_cpus = stats["cpu_stats"].get("online_cpus", 1)
                    if system_delta > 0 and cpu_delta > 0:
                        cpu_pct = (cpu_delta / system_delta) * num_cpus * 100.0
                    mem_usage = stats["memory_stats"].get("usage", 0)
                    mem_mb = mem_usage / (1024 * 1024)
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

        return result

    async def _collect_remote(self) -> dict[str, Any]:
        """Collect via SSH docker CLI commands."""
        result: dict[str, Any] = {
            "docker_containers": [],
            "proxy_container_running": False,
            "proxy_container_started_at": None,
        }

        if self._remote is None:
            return result

        connected = await self._remote.ensure_connected()
        if not connected:
            return result

        # Get container inspect JSON for all containers
        names_str = " ".join(self.container_names)
        cmd = f"docker inspect {names_str} 2>/dev/null || echo '[]'"
        inspect_result = await self._remote.run(cmd, timeout=15.0)

        containers_data = []
        try:
            containers_data = json.loads(inspect_result["stdout"] or "[]")
        except json.JSONDecodeError:
            containers_data = []

        if not isinstance(containers_data, list):
            containers_data = []

        # Get docker stats for each container (no-stream)
        for name in self.container_names:
            stats_cmd = f"docker stats --no-stream --format '{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.NetIO}}}}' {name} 2>/dev/null || echo '0.00%||'"
            stats_result = await self._remote.run(stats_cmd, timeout=10.0)
            stats_line = stats_result["stdout"] or ""

            cpu_pct = 0.0
            mem_mb = 0.0
            net_rx = 0
            net_tx = 0

            if stats_line:
                parts = stats_line.split("|")
                if len(parts) >= 1:
                    try:
                        cpu_pct = float(parts[0].replace("%", "").strip())
                    except ValueError:
                        pass
                if len(parts) >= 2:
                    # Format: "123.4MiB / 1.2GiB"
                    mem_str = parts[1].split("/")[0].strip()
                    # Convert to MB
                    try:
                        if "GiB" in mem_str:
                            mem_mb = float(mem_str.replace("GiB", "")) * 1024
                        elif "MiB" in mem_str:
                            mem_mb = float(mem_str.replace("MiB", ""))
                        elif "KiB" in mem_str:
                            mem_mb = float(mem_str.replace("KiB", "")) / 1024
                        else:
                            mem_mb = float(mem_str) / (1024 * 1024)
                    except ValueError:
                        pass
                if len(parts) >= 3:
                    # Format: "1.2GB / 500MB"
                    net_parts = parts[2].split("/")
                    if len(net_parts) >= 2:
                        try:
                            net_rx = _parse_bytes(net_parts[0].strip())
                            net_tx = _parse_bytes(net_parts[1].strip())
                        except (ValueError, IndexError):
                            pass

            # Find container inspect data
            inspect_info = next((c for c in containers_data if c.get("Name", "").lstrip("/") == name), None)
            running = False
            status = "NOT FOUND"
            started_at = None

            if inspect_info:
                state = inspect_info.get("State", {})
                running = state.get("Running", False)
                status = state.get("Status", "unknown").upper()
                started = state.get("StartedAt", "")
                if started:
                    try:
                        from datetime import datetime, timezone
                        dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        started_at = dt.timestamp()
                    except Exception:
                        pass

            container_info = {
                "name": name,
                "status": status,
                "cpu_percent": round(cpu_pct, 1),
                "mem_mb": round(mem_mb, 1),
                "net_rx": net_rx,
                "net_tx": net_tx,
                "running": running,
            }
            result["docker_containers"].append(container_info)

            if name == "socks5" and running:
                result["proxy_container_running"] = True
                result["proxy_container_started_at"] = started_at

        return result

    async def collect(self) -> None:
        """Collect docker container health."""
        if self._remote:
            result = await self._collect_remote()
        else:
            result = await asyncio.to_thread(self._collect_local)
        self.data_store.update(result)


def _parse_bytes(s: str) -> int:
    """Parse a human-readable byte string like '1.2GB' or '500MB' into bytes."""
    s = s.strip().upper()
    if s.endswith("GB"):
        return int(float(s[:-2]) * 1024 * 1024 * 1024)
    elif s.endswith("MB"):
        return int(float(s[:-2]) * 1024 * 1024)
    elif s.endswith("KB"):
        return int(float(s[:-2]) * 1024)
    elif s.endswith("B"):
        return int(float(s[:-1]))
    return int(float(s))