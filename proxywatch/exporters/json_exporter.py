"""Export current metrics snapshot as JSON."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def export_json(data_store, filepath: str) -> None:
    """Export the current data store snapshot as a JSON file.

    Args:
        data_store: The DataStore instance.
        filepath: Path to write the JSON file.
    """
    snapshot = _build_snapshot(data_store)
    snapshot["exported_at"] = time.time()
    snapshot["exported_at_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as fh:
        json.dump(snapshot, fh, indent=2, default=str)


def _build_snapshot(data_store) -> dict[str, Any]:
    """Build a serializable snapshot from the data store."""
    return {
        "system": {
            "hostname": data_store.get_sync("system_hostname", ""),
            "time": data_store.get_sync("system_time", ""),
            "uptime_seconds": data_store.get_sync("system_uptime", 0),
            "cpu_percent": data_store.get_sync("system_cpu", 0.0),
            "ram_percent": data_store.get_sync("system_ram", 0.0),
            "disk_percent": data_store.get_sync("system_disk", 0.0),
        },
        "proxy": {
            "online": data_store.get_sync("proxy_online", False),
            "uptime_seconds": data_store.get_sync("proxy_uptime", 0),
            "active_connections": data_store.get_sync("connections_active", 0),
            "requests_per_minute": data_store.get_sync("requests_per_minute", 0),
        },
        "bandwidth": {
            "rx_bps": data_store.get_sync("bandwidth_rx_bps", 0.0),
            "tx_bps": data_store.get_sync("bandwidth_tx_bps", 0.0),
            "total_rx_bytes": data_store.get_sync("bandwidth_total_rx", 0),
            "total_tx_bytes": data_store.get_sync("bandwidth_total_tx", 0),
            "daily_rx_bytes": data_store.get_sync("bandwidth_daily_rx", 0),
            "daily_tx_bytes": data_store.get_sync("bandwidth_daily_tx", 0),
            "peak_bps_today": data_store.get_sync("bandwidth_peak_bps_today", 0.0),
            "peak_connections_today": data_store.get_sync("bandwidth_peak_conns_today", 0),
        },
        "connections": data_store.get_sync("connections_details", []),
        "top_destinations": data_store.get_sync("top_destinations", []),
        "docker_containers": data_store.get_sync("docker_containers", []),
        "security_alerts": data_store.get_sync("security_alerts", []),
    }