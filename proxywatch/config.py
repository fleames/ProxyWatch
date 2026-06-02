"""Configuration loader with YAML parsing and validation — supports remote VPS mode."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "trusted_clients": [
        "192.168.1.100",
        "10.0.0.50",
    ],
    "proxy_container": "socks5",
    "proxy_port": 1081,
    "refresh_rate": 1,
    "alert_thresholds": {
        "bandwidth_mbps": 100,
        "connections_per_minute": 50,
        "unknown_client_alert": True,
        "container_restart_alert": True,
        "port_down_alert": True,
    },
    "export": {
        "json_path": "/tmp/proxywatch_metrics.json",
        "csv_path": "/tmp/proxywatch_metrics.csv",
    },
    "network_interface": "eth0",
    "log_lines": 50,
    "graph_history_seconds": 300,
    # Remote VPS connection (optional — if set, runs in remote mode)
    "remote": {
        "host": "",
        "port": 22,
        "user": "root",
        "key_path": "",
        "password": "",
    },
    # SSH terminal / full VPS manager features
    "terminal": {
        "enabled": True,
        "history_size": 2000,
        "font_size": "medium",
    },
    "docker_containers": ["socks5", "wg-easy"],
}

CONFIG_SEARCH_PATHS = [
    os.environ.get("PROXYWATCH_CONFIG", ""),
    "config.yaml",
    "config.yml",
    os.path.expanduser("~/.config/proxywatch/config.yaml"),
    os.path.expanduser("~/.config/proxywatch/config.yml"),
    "/etc/proxywatch/config.yaml",
    "/etc/proxywatch/config.yml",
]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file, falling back to defaults.

    Args:
        config_path: Explicit path to config file. If None, searches default paths.

    Returns:
        Merged configuration dictionary.
    """
    config = DEFAULT_CONFIG.copy()

    paths_to_try = [config_path] if config_path else CONFIG_SEARCH_PATHS

    for path in paths_to_try:
        if path and Path(path).is_file():
            with open(path, "r") as fh:
                loaded = yaml.safe_load(fh) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config file {path} must contain a YAML mapping.")
            config = _deep_merge(config, loaded)
            break

    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate configuration values and raise on critical problems.

    Args:
        config: The configuration dictionary to validate.

    Raises:
        ValueError: If a critical config value is invalid.
    """
    if not isinstance(config.get("trusted_clients"), list):
        raise ValueError("trusted_clients must be a list of IP strings.")
    if not isinstance(config.get("proxy_container"), str) or not config["proxy_container"]:
        raise ValueError("proxy_container must be a non-empty string.")
    if not isinstance(config.get("proxy_port"), int) or not (1 <= config["proxy_port"] <= 65535):
        raise ValueError("proxy_port must be an integer between 1 and 65535.")
    if not isinstance(config.get("refresh_rate"), (int, float)) or config["refresh_rate"] < 0.1:
        raise ValueError("refresh_rate must be a float >= 0.1 seconds.")
    if not isinstance(config.get("log_lines"), int) or config["log_lines"] < 1:
        raise ValueError("log_lines must be a positive integer.")

    # Validate remote config if host is set
    remote = config.get("remote", {})
    if remote.get("host"):
        if not isinstance(remote.get("port"), int) or not (1 <= remote["port"] <= 65535):
            raise ValueError("remote.port must be an integer between 1 and 65535.")
        if not remote.get("user"):
            raise ValueError("remote.user must be set when remote.host is specified.")
        if not remote.get("key_path") and not remote.get("password"):
            raise ValueError("remote.key_path or remote.password must be set.")


def is_remote_mode(config: dict[str, Any]) -> bool:
    """Return True if the config specifies a remote VPS connection."""
    remote = config.get("remote", {})
    return bool(remote.get("host"))