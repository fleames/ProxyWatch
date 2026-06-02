#!/usr/bin/env python3
"""ProxyWatch — Real-Time SOCKS5 Proxy Monitoring Dashboard.

Usage:
    python main.py
    python main.py --config /path/to/config.yaml

Requirements:
    Python 3.12+, Linux
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Entry point for ProxyWatch dashboard."""
    parser = argparse.ArgumentParser(
        description="ProxyWatch — Real-Time SOCKS5 Proxy Monitoring Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --config /etc/proxywatch/config.yaml

Hotkeys:
  Q              Quit
  R              Refresh
  L              Clear logs
  D              Toggle Docker panel
  N              Toggle Network graph
  S              Toggle Security panel
  Ctrl+E         Export metrics
        """,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="ProxyWatch v1.0.0",
    )

    args = parser.parse_args()

    # Verify we're on Linux
    if sys.platform != "linux":
        print(
            "[!] ProxyWatch requires Linux. "
            "It reads /proc/net/tcp, /sys/class/net/*, and uses Docker SDK.",
            file=sys.stderr,
        )
        sys.exit(1)

    from proxywatch.app import ProxyWatchApp

    app = ProxyWatchApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()