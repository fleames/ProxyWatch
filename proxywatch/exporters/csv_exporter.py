"""Export metrics as CSV."""

from __future__ import annotations

import csv
import time
from pathlib import Path


def export_csv(data_store, filepath: str) -> None:
    """Export proxy metrics as a timestamped CSV file.

    Appends a row with the current metric snapshot.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = path.is_file()

    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp_epoch": int(time.time()),
        "hostname": data_store.get_sync("system_hostname", ""),
        "cpu_percent": round(data_store.get_sync("system_cpu", 0.0) * 100, 1),
        "ram_percent": round(data_store.get_sync("system_ram", 0.0) * 100, 1),
        "disk_percent": round(data_store.get_sync("system_disk", 0.0) * 100, 1),
        "proxy_online": 1 if data_store.get_sync("proxy_online", False) else 0,
        "proxy_uptime_seconds": data_store.get_sync("proxy_uptime", 0),
        "active_connections": data_store.get_sync("connections_active", 0),
        "requests_per_minute": data_store.get_sync("requests_per_minute", 0),
        "bandwidth_rx_bps": round(data_store.get_sync("bandwidth_rx_bps", 0.0), 1),
        "bandwidth_tx_bps": round(data_store.get_sync("bandwidth_tx_bps", 0.0), 1),
        "total_rx_bytes": data_store.get_sync("bandwidth_total_rx", 0),
        "total_tx_bytes": data_store.get_sync("bandwidth_total_tx", 0),
        "daily_rx_bytes": data_store.get_sync("bandwidth_daily_rx", 0),
        "daily_tx_bytes": data_store.get_sync("bandwidth_daily_tx", 0),
        "peak_bps_today": round(data_store.get_sync("bandwidth_peak_bps_today", 0.0), 1),
        "peak_connections_today": data_store.get_sync("bandwidth_peak_conns_today", 0),
        "alert_count": len(data_store.get_sync("security_alerts", [])),
    }

    fieldnames = list(row.keys())

    with open(path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)