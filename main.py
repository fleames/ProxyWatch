#!/usr/bin/env python3
"""ProxyWatch — Real-Time SOCKS5 Proxy Monitoring Dashboard + VPS Manager.

Usage:
    python main.py
    python main.py --config /path/to/config.yaml

Runs on:
    - Linux (local mode: reads /proc, /sys, Docker SDK directly)
    - Windows/macOS (remote mode: connects to Linux VPS via SSH)
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Entry point for ProxyWatch dashboard."""
    parser = argparse.ArgumentParser(
        description="ProxyWatch — Real-Time SOCKS5 Proxy Monitoring Dashboard + VPS Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --config config.yaml

Hotkeys:
  Q              Quit
  R              Refresh
  L              Clear logs
  D              Toggle Docker panel
  N              Toggle Network graph
  S              Toggle Security panel
  T              Toggle SSH Terminal (full VPS control)
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
        version="ProxyWatch v2.0.0",
    )

    args = parser.parse_args()

    # Show platform warning if on Linux without remote config
    # but don't block execution — remote mode works everywhere
    from proxywatch.app import ProxyWatchApp

    app = ProxyWatchApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()