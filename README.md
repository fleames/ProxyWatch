# ProxyWatch

**Real-Time SOCKS5 Proxy Monitoring Dashboard**

A production-quality terminal dashboard for monitoring a SOCKS5 proxy (Docker container) on Linux VPS. Provides live metrics, connections, bandwidth, logs, security alerts, and more — all in a beautiful htop/btop-style TUI.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Linux-black.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Features

- **8 Real-Time Panels**: Proxy status, live connections, top destinations, proxy logs, network graph, trusted client stats, Docker health, security alerts
- **Non-blocking Architecture**: Fully async collectors using asyncio, zero subprocess calls for network data
- **Textual TUI**: Rich, responsive terminal UI with dark theme, syntax-highlighted logs, DataTables, ASCII bar graphs
- **Security Monitor**: Alerts for unknown IPs, bandwidth spikes, connection surges, container restarts, port down events
- **Metrics Export**: Auto-export to JSON and CSV every tick
- **Docker-Aware**: Monitors socks5 and wg-easy containers via Docker SDK
- **Performance**: <100 MB RAM, <2% CPU on modern VPS

---

## Screenshots

```
┌──────────────────────────────────────────────────────────────┐
│  vps-01 │ 2026-06-02 21:30:00 │ UP 14d 3h │ CPU 2.3% │ ...  │
├──────────────────────┬───────────────────────┬───────────────┤
│  SOCKS5 STATUS       │  LIVE CONNECTIONS     │  TOP DEST     │
│  Status: ONLINE      │  IP -> Dest:Port      │  IP / C / BW  │
│  Active: 14          │  2.110...→198.54:443  │  198.54...    │
│  Req/min: 203        │  89.167...→184.86:80  │  184.86...    │
├──────────────────────┴───────────────────────┴───────────────┤
│  PROXY LOGS                                                   │
│  [INFO] Connection from allowed IP address                    │
│  [ERR] splice: connection timed out                           │
├──────────────────────┬───────────────────────┬───────────────┤
│  NETWORK GRAPH       │  TRUSTED CLIENTS      │  DOCKER HLTH  │
│  ↓ 12.3 Mbps ████    │  IP / Conns / RX / TX │  socks5 ONL   │
│  ↑ 4.1 Mbps  ██      │  2.110... 1054 18 GB  │  wg-easy HLTH │
├──────────────────────┴───────────────────────┴───────────────┤
│  SECURITY ALERTS: ✓ No alerts                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Requirements

- **Linux** (Ubuntu 24.04+ recommended)
- **Python 3.12+**
- **Docker Engine** (with `/var/run/docker.sock` accessible)
- **SOCKS5 Docker container** named `socks5` (configurable)
- **Terminal** with 256-color and Unicode support

---

## Installation

### Option 1: Direct (Recommended for VPS)

```bash
# Clone or copy files to your server
git clone <repo-url> /opt/proxywatch
cd /opt/proxywatch

# Create venv and install dependencies
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Edit configuration
nano config.yaml

# Run (activates venv automatically)
./run.sh
```

### Option 2: Docker

```bash
# Build and run (requires host pid/network + docker.sock)
docker build -t proxywatch .
docker run -it --rm \
    --pid=host \
    --net=host \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v $(pwd)/config.yaml:/app/config.yaml:ro \
    proxywatch
```

### Option 3: Docker Compose

```bash
# Start the full stack (socks5 + wg-easy + proxywatch)
docker compose --profile monitoring up -d

# Attach to the dashboard
docker attach proxywatch
```

---

## Configuration

Edit `config.yaml`:

```yaml
# Trusted client IPs (unknown IPs trigger security alerts)
trusted_clients:
  - 192.168.1.100
  - 10.0.0.50

# Docker container name for the SOCKS5 proxy
proxy_container: socks5

# Port the SOCKS5 proxy listens on
proxy_port: 1081

# Refresh interval (seconds)
refresh_rate: 1

# Network interface for bandwidth monitoring
network_interface: eth0

# Log buffer size
log_lines: 50

# Rolling graph history (seconds)
graph_history_seconds: 300

# Alert thresholds
alert_thresholds:
  bandwidth_mbps: 100
  connections_per_minute: 50
  unknown_client_alert: true
  container_restart_alert: true
  port_down_alert: true

# Export paths
export:
  json_path: /tmp/proxywatch_metrics.json
  csv_path: /tmp/proxywatch_metrics.csv
```

Configuration is loaded from (in priority order):
1. `--config` CLI argument
2. `PROXYWATCH_CONFIG` environment variable
3. `./config.yaml`
4. `~/.config/proxywatch/config.yaml`
5. `/etc/proxywatch/config.yaml`

---

## Hotkeys

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `R` | Refresh |
| `L` | Clear proxy logs |
| `D` | Toggle Docker health panel |
| `N` | Toggle Network graph panel |
| `S` | Toggle Security alerts panel |
| `Ctrl+E` | Export metrics to JSON/CSV |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    MAIN ASYNC LOOP                    │
│                                                      │
│  SystemCollector ──┐                                 │
│  DockerCollector ──┤                                 │
│  ConnectionCollector ──┤                             │
│  BandwidthCollector ──┤──> DataStore <── Widgets     │
│  ProxyStatsCollector ──┤    (dict)      (Textual)    │
│  DestinationsCollector ──┤                           │
│  ProxyLogsCollector ──┤                              │
│  SecurityCollector ──┘                               │
│                                                      │
│  Exporters (JSON/CSV) ──> /tmp/proxywatch_*.json     │
└──────────────────────────────────────────────────────┘
```

### Data Sources

| Metric | Source |
|--------|--------|
| CPU / RAM / Disk | `psutil` library |
| Docker container stats | `docker` Python SDK |
| Active TCP connections | `/proc/net/tcp`, `/proc/net/tcp6` |
| Bandwidth (bytes/sec) | `/sys/class/net/<iface>/statistics/` |
| Container logs | Docker SDK log stream |
| Container uptime | Docker SDK container inspect |

**No subprocess calls to `ss`, `netstat`, or `docker` CLI** — all parsing uses stable procfs reads and official Python APIs.

---

## Project Structure

```
proxywatch/
├── main.py                          # Entry point
├── config.yaml                      # User configuration
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container build
├── docker-compose.yml               # Full stack
├── README.md                        # This file
│
└── proxywatch/
    ├── __init__.py
    ├── app.py                       # Textual App (layout, hotkeys)
    ├── splash.py                    # Splash screen
    ├── config.py                    # YAML config loader
    ├── collectors/
    │   ├── base.py                  # DataStore + BaseCollector
    │   ├── system.py                # CPU/RAM/Disk/Uptime
    │   ├── docker_collector.py      # Container health
    │   ├── connections.py           # /proc/net/tcp parser
    │   ├── bandwidth.py             # RX/TX rates + history
    │   ├── proxy_stats.py           # Aggregate stats
    │   ├── destinations.py          # Top dest IPs
    │   ├── proxy_logs.py            # Docker log stream
    │   └── security.py             # Alert detection
    ├── widgets/
    │   ├── header.py                # Top bar
    │   ├── proxy_status.py          # Panel 1
    │   ├── client_connections.py    # Panel 2
    │   ├── top_destinations.py      # Panel 3
    │   ├── proxy_logs.py            # Panel 4
    │   ├── network_graph.py         # Panel 5
    │   ├── trusted_clients.py       # Panel 6
    │   ├── docker_health.py         # Panel 7
    │   └── security_alerts.py       # Panel 8
    ├── exporters/
    │   ├── json_exporter.py
    │   └── csv_exporter.py
    └── utils/
        ├── net_parser.py            # /proc parsers
        └── formatting.py            # Human-readable formatters
```

---

## Performance

Designed to run efficiently on modest VPS resources:

- **RAM**: <100 MB RSS (Python + Textual + collectors)
- **CPU**: <2% on a single vCPU (mostly I/O wait on procfs)
- **Disk I/O**: Minimal — reads `/proc` and `/sys` virtual filesystems
- **Network**: No external API calls; local Docker socket only

All collectors are cooperative async coroutines. No threads are spawned except for Docker SDK calls which use `asyncio.to_thread()`.

---

## Security Notes

- ProxyWatch requires access to `/var/run/docker.sock` — this grants **full Docker control**. Run with caution.
- The security monitor detects unknown IPs by comparing against `trusted_clients` in config.yaml.
- All data stays on the local machine. No telemetry, no phoning home.
- Consider running behind `tmux` or `screen` for persistent sessions.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: textual` | `pip install -r requirements.txt` |
| `Permission denied: /proc/net/tcp` | Run as root or with `CAP_NET_ADMIN` |
| `Docker connection refused` | Ensure `/var/run/docker.sock` is mounted |
| `No containers found` | Verify `proxy_container` name in config.yaml |
| `Bandwidth shows 0` | Check `network_interface` matches your interface (`ip a`) |
| `Logs not streaming` | Ensure the `socks5` container exists and is running |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Support

For issues, feature requests, or contributions, open an issue on the repository.

---

**ProxyWatch** — Know your proxy. Monitor everything.