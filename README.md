# ProxyWatch v2.0

**Real-Time SOCKS5 Proxy Monitoring Dashboard + VPS Manager**

A production-quality terminal dashboard for monitoring a SOCKS5 proxy (Docker container) on a Linux VPS. Provides live metrics, connections, bandwidth, logs, security alerts, an SSH terminal for full VPS control — all in a beautiful htop/btop-style TUI.

## New in v2.0

- **Cross-Platform**: Runs on Windows, macOS, and Linux
- **Remote Mode**: Connects to any Linux VPS via SSH — monitors proxy + full VPS management
- **Built-in SSH Terminal**: Press `T` to open a full interactive terminal on your VPS
- **Auto-detection**: Local mode (Linux, reads /proc directly) or remote mode (SSH) — just configure it

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-black.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Features

### Dashboard (8 Real-Time Panels)
- **Proxy Status**: Online/offline, active connections, requests/min, uptime
- **Live Connections**: Source IP → Destination with duration
- **Top Destinations**: IP / connections / bandwidth ranked
- **Proxy Logs**: Color-coded log stream (INFO=green, WARN=yellow, ERR=red)
- **Network Graph**: ASCII bandwidth history graph (RX/TX)
- **Trusted Clients**: Per-client connection counts and traffic
- **Docker Health**: Container status, CPU%, memory, network I/O
- **Security Alerts**: Unknown IPs, bandwidth spikes, connection surges, container restart detection

### SSH Terminal (VPS Manager)
- Full interactive command shell on your VPS
- Execute any Linux command: `docker`, `systemctl`, `htop`, `df`, `ss`, `nethogs`, etc.
- Built-in `help`, `clear`, `history` commands
- Command output displayed inline with rich formatting

### Cross-Platform Architecture
- **Local Mode (Linux)**: Reads `/proc/net/tcp`, `/sys/class/net/*`, Docker SDK directly
- **Remote Mode (Windows/macOS)**: All data collected over SSH from the VPS
- **No subprocess calls** — all parsing uses stable APIs

### Metrics Export
- Auto-export to JSON and CSV every refresh tick
- Manual export via `Ctrl+E`

---

## Requirements

- **Python 3.12+**
- **For remote mode**: SSH access to a Linux VPS
- **For local mode**: Linux with Docker Engine
- **VPS side**: Docker containers (`socks5`, `wg-easy`)
- **Terminal** with 256-color and Unicode support

---

## Installation

### Windows

```batch
git clone https://github.com/fleames/ProxyWatch.git
cd ProxyWatch

python -m venv venv
venv\Scripts\pip install -r requirements.txt

# Edit config.yaml — set your VPS IP under remote:
notepad config.yaml

# Run
run.bat
```

### Linux / macOS

```bash
git clone https://github.com/fleames/ProxyWatch.git /opt/proxywatch
cd /opt/proxywatch

python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Edit configuration
nano config.yaml

# Run (activates venv automatically)
./run.sh
```

---

## Configuration

Edit `config.yaml`:

```yaml
# === REMOTE MODE (Windows/macOS → VPS) ===
remote:
  host: "123.45.67.89"     # Your VPS IP
  port: 22
  user: "root"
  key_path: "~/.ssh/id_rsa"  # SSH key path
  # password: ""             # Or use password

# === SOCKS5 PROXY ===
proxy_container: socks5
proxy_port: 1081
trusted_clients:
  - 192.168.1.100
  - 10.0.0.50

# === MONITORING ===
refresh_rate: 1              # seconds between updates
network_interface: eth0      # bandwidth monitoring interface
log_lines: 50                # log buffer size
graph_history_seconds: 300   # network graph history

# === DOCKER CONTAINERS ===
docker_containers:
  - socks5
  - wg-easy

# === ALERTS ===
alert_thresholds:
  bandwidth_mbps: 100
  connections_per_minute: 50
  unknown_client_alert: true
  container_restart_alert: true
  port_down_alert: true

# === EXPORT ===
export:
  json_path: /tmp/proxywatch_metrics.json
  csv_path: /tmp/proxywatch_metrics.csv
```

---

## Hotkeys

| Key | Action |
|-----|--------|
| `Q` / `Ctrl+C` | Quit |
| `R` | Refresh |
| `L` | Clear proxy logs |
| `D` | Toggle Docker health panel |
| `N` | Toggle Network graph panel |
| `S` | Toggle Security alerts panel |
| **`T`** | **Toggle SSH Terminal (full VPS control)** |
| `Ctrl+E` | Export metrics to JSON/CSV |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ProxyWatch TUI (Textual)              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Proxy   │  │  Live    │  │   Top    │              │
│  │  Status  │  │  Conns   │  │  Dests   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌─────────────────────────────────────────┐           │
│  │           Proxy Logs                     │           │
│  └─────────────────────────────────────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Network  │  │ Trusted  │  │ Docker   │              │
│  │  Graph   │  │ Clients  │  │  Health  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌─────────────────────────────────────────┐           │
│  │         Security Alerts                  │           │
│  └─────────────────────────────────────────┘           │
│  ┌─────────────────────────────────────────┐           │
│  │  ⚡ SSH TERMINAL (full VPS control)      │  Press T  │
│  │  root@vps:~$ _                           │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│         LOCAL MODE            REMOTE MODE               │
│     (Linux /proc, /sys)    (SSH → Linux VPS)            │
│     ┌──────────────┐      ┌──────────────┐              │
│     │  psutil      │      │  asyncssh    │              │
│     │  docker SDK  │      │  ssh run cmd │              │
│     │  /proc/net   │      │  cat /proc   │              │
│     └──────────────┘      └──────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### Data Sources

| Metric | Local Mode | Remote Mode |
|--------|-----------|-------------|
| CPU / RAM / Disk | `psutil` | `top`, `free`, `df` via SSH |
| Docker stats | Docker SDK | `docker stats --no-stream` via SSH |
| TCP connections | `/proc/net/tcp` | `cat /proc/net/tcp` via SSH |
| Bandwidth | `/sys/class/net/` | `cat /sys/class/net/` via SSH |
| Container logs | Docker SDK | `docker logs --tail N` via SSH |

---

## SSH Terminal Commands

The built-in SSH terminal (`T` key) supports all VPS commands:

```bash
# Docker management
docker ps
docker stats --no-stream
docker logs socks5
docker restart socks5

# System monitoring
htop
df -h
free -h
uptime
ss -tnp
nethogs eth0

# Service management
systemctl status docker
journalctl -f
```

Built-in terminal commands: `help`, `clear`, `history`, `exit`

---

## Performance

- **RAM**: <100 MB RSS (Python + Textual + collectors)
- **CPU**: <2% on a single vCPU
- **SSH overhead**: ~50ms per command batch (commands run in parallel)
- **All collectors are cooperative async coroutines** — no thread spawning except for SSH reconnect

---

## Security Notes

- SSH keys should use `~/.ssh/id_rsa` or specify a custom path
- Password auth is supported but not recommended for production
- SSH host key checking is disabled for convenience — enable it by removing `known_hosts=None` in `remote.py`
- All data stays on the local machine. No telemetry, no phoning home.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: asyncssh` | `pip install -r requirements.txt` |
| `SSH connection failed` | Verify `remote.host` and credentials in config.yaml |
| `Permission denied` | Check SSH key path or password |
| `docker: command not found` | Ensure Docker is installed on the VPS |
| `Bandwidth shows 0` | Check `network_interface` matches VPS interface (`ip a`) |
| Terminal not responding | Press `Ctrl+C` or `Q` to quit |

---

## License

MIT License

---

**ProxyWatch v2.0** — Know your proxy. Control your VPS. All in one terminal.