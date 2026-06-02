"""Safe, subprocess-free parsers for Linux network data — local and remote modes.

In local mode: reads /proc/net/* and /sys/class/net/* files directly.
In remote mode: parses command output strings from SSH remote execution.
"""

from __future__ import annotations

import socket
import struct
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Optional

# ---------------------------------------------------------------------------
# /proc/net/tcp  and  /proc/net/tcp6  parsers
# ---------------------------------------------------------------------------


def hex_to_ipv4(hex_str: str) -> str:
    """Convert a /proc/net IPv4 hex address (e.g. '0100007F') to dotted-decimal."""
    try:
        packed = bytes.fromhex(hex_str)
        return str(IPv4Address(packed))
    except (ValueError, struct.error):
        return "0.0.0.0"


def hex_to_ipv6(hex_str: str) -> str:
    """Convert a /proc/net IPv6 hex address (32 hex digits) to colon-hex notation."""
    try:
        raw = bytes.fromhex(hex_str)
        return str(IPv6Address(raw))
    except (ValueError, struct.error):
        return "::"


_IPV4_LOOPBACK_CANDIDATES = {"127.0.0.1", "0.0.0.0", "127.0.0.0"}
_IPV6_LOOPBACK_CANDIDATES = {"::1", "::", "::ffff:127.0.0.1"}


def parse_proc_net_socket_line(line: str, ipv6: bool = False) -> Optional[dict[str, object]]:
    """Parse one line from /proc/net/tcp or /proc/net/tcp6.

    Returns a dict with keys:
        sl, local_address, local_port, rem_address, rem_port,
        st, tx_queue, rx_queue, tr, tm_when, retrnsmt,
        uid, timeout, inode
    or None if the line is a header or unparseable.
    """
    parts = line.strip().split()
    if not parts or parts[0] == "sl":
        return None

    if len(parts) < 12:
        return None

    try:
        sl = parts[0].rstrip(":")
        local_pair = parts[1]
        rem_pair = parts[2]
        st_hex = parts[3]
        tx_rx = parts[4]
        tr_tm = parts[5]
        retrnsmt = parts[6]
        uid = int(parts[7])
        timeout = int(parts[8])
        inode = int(parts[9])
    except (IndexError, ValueError):
        return None

    local_addr_hex, local_port_hex = local_pair.split(":")
    rem_addr_hex, rem_port_hex = rem_pair.split(":")

    local_ip = hex_to_ipv6(local_addr_hex) if ipv6 else hex_to_ipv4(local_addr_hex)
    rem_ip = hex_to_ipv6(rem_addr_hex) if ipv6 else hex_to_ipv4(rem_addr_hex)
    local_port = int(local_port_hex, 16)
    rem_port = int(rem_port_hex, 16)
    state = int(st_hex, 16)

    tx_queue_hex, rx_queue_hex = tx_rx.split(":")
    tx_queue = int(tx_queue_hex, 16)
    rx_queue = int(rx_queue_hex, 16)

    tr_hex, tm_when_hex = tr_tm.split(":")
    tr = int(tr_hex, 16) if tr_hex else 0
    tm_when = int(tm_when_hex, 16) if tm_when_hex else 0

    return {
        "sl": sl,
        "local_address": local_ip,
        "local_port": local_port,
        "rem_address": rem_ip,
        "rem_port": rem_port,
        "st": state,
        "tx_queue": tx_queue,
        "rx_queue": rx_queue,
        "tr": tr,
        "tm_when": tm_when,
        "retrnsmt": int(retrnsmt, 16) if retrnsmt else 0,
        "uid": uid,
        "timeout": timeout,
        "inode": inode,
    }


_TCP_STATE_NAMES: dict[int, str] = {
    0x01: "ESTABLISHED",
    0x02: "SYN_SENT",
    0x03: "SYN_RECV",
    0x04: "FIN_WAIT1",
    0x05: "FIN_WAIT2",
    0x06: "TIME_WAIT",
    0x07: "CLOSE",
    0x08: "CLOSE_WAIT",
    0x09: "LAST_ACK",
    0x0A: "LISTEN",
    0x0B: "CLOSING",
}


def tcp_state_name(st: int) -> str:
    """Return human-readable TCP state name for hex code."""
    return _TCP_STATE_NAMES.get(st, f"UNKNOWN(0x{st:02X})")


def is_established(st: int) -> bool:
    """Return True if the TCP state is ESTABLISHED."""
    return st == 0x01


# ---------------------------------------------------------------------------
# /proc/net/dev  parser
# ---------------------------------------------------------------------------

_INTERFACE_LINE_THRESHOLD = 4


def parse_proc_net_dev_line(line: str) -> Optional[dict[str, object]]:
    """Parse one data line from /proc/net/dev.

    Returns dict with keys:
        interface, rx_bytes, rx_packets, rx_errs, rx_drop, rx_fifo,
        rx_frame, rx_compressed, rx_multicast,
        tx_bytes, tx_packets, tx_errs, tx_drop, tx_fifo,
        tx_colls, tx_carrier, tx_compressed
    or None if the line is a header.
    """
    parts = line.strip().split()
    if len(parts) < _INTERFACE_LINE_THRESHOLD:
        return None

    iface = parts[0].rstrip(":")
    if iface in ("Inter-", "face") or iface.startswith("Inter"):
        return None

    try:
        stats = [int(p) for p in parts[1:]]
    except ValueError:
        return None

    if len(stats) < 16:
        return None

    return {
        "interface": iface,
        "rx_bytes": stats[0],
        "rx_packets": stats[1],
        "rx_errs": stats[2],
        "rx_drop": stats[3],
        "rx_fifo": stats[4],
        "rx_frame": stats[5],
        "rx_compressed": stats[6],
        "rx_multicast": stats[7],
        "tx_bytes": stats[8],
        "tx_packets": stats[9],
        "tx_errs": stats[10],
        "tx_drop": stats[11],
        "tx_fifo": stats[12],
        "tx_colls": stats[13],
        "tx_carrier": stats[14],
        "tx_compressed": stats[15],
    }


# ---------------------------------------------------------------------------
# Local /proc file readers (fallback for non-remote mode)
# ---------------------------------------------------------------------------


def read_proc_net_tcp() -> list[dict[str, object]]:
    """Read /proc/net/tcp and return list of parsed socket entries."""
    try:
        with open("/proc/net/tcp", "r") as fh:
            lines = fh.readlines()
    except (FileNotFoundError, PermissionError):
        return []

    entries: list[dict[str, object]] = []
    for line in lines:
        entry = parse_proc_net_socket_line(line, ipv6=False)
        if entry is not None:
            entries.append(entry)
    return entries


def read_proc_net_tcp6() -> list[dict[str, object]]:
    """Read /proc/net/tcp6 and return list of parsed socket entries."""
    try:
        with open("/proc/net/tcp6", "r") as fh:
            lines = fh.readlines()
    except (FileNotFoundError, PermissionError):
        return []

    entries: list[dict[str, object]] = []
    for line in lines:
        entry = parse_proc_net_socket_line(line, ipv6=True)
        if entry is not None:
            entries.append(entry)
    return entries


def read_proc_net_dev() -> list[dict[str, object]]:
    """Read /proc/net/dev and return list of per-interface statistics."""
    try:
        with open("/proc/net/dev", "r") as fh:
            lines = fh.readlines()
    except (FileNotFoundError, PermissionError):
        return []

    entries: list[dict[str, object]] = []
    for line in lines:
        entry = parse_proc_net_dev_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def read_iface_bytes(iface: str) -> tuple[int, int]:
    """Read current RX and TX byte counters for a network interface.

    Returns (rx_bytes, tx_bytes) from /sys/class/net/<iface>/statistics/.
    """
    base = f"/sys/class/net/{iface}/statistics"
    try:
        with open(f"{base}/rx_bytes", "r") as fh:
            rx = int(fh.read().strip())
    except (FileNotFoundError, PermissionError, ValueError):
        rx = 0
    try:
        with open(f"{base}/tx_bytes", "r") as fh:
            tx = int(fh.read().strip())
    except (FileNotFoundError, PermissionError, ValueError):
        tx = 0
    return rx, tx


# ---------------------------------------------------------------------------
# Parsers from raw text (for remote SSH output)
# ---------------------------------------------------------------------------


def parse_proc_output(text: str, ipv6: bool = False) -> list[dict[str, object]]:
    """Parse raw /proc/net/tcp text output into socket entries."""
    entries: list[dict[str, object]] = []
    for line in text.splitlines():
        entry = parse_proc_net_socket_line(line, ipv6=ipv6)
        if entry is not None:
            entries.append(entry)
    return entries


def parse_proc_net_dev_output(text: str) -> list[dict[str, object]]:
    """Parse raw /proc/net/dev text output into interface stats."""
    entries: list[dict[str, object]] = []
    for line in text.splitlines():
        entry = parse_proc_net_dev_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def parse_interface_bytes(rx_text: str, tx_text: str) -> tuple[int, int]:
    """Parse raw rx_bytes and tx_bytes from command output."""
    try:
        rx = int(rx_text.strip())
    except (ValueError, TypeError):
        rx = 0
    try:
        tx = int(tx_text.strip())
    except (ValueError, TypeError):
        tx = 0
    return rx, tx


def get_connection_summary(
    port: int,
) -> tuple[int, int, list[dict[str, object]]]:
    """Return (established_count, listening_count, connections_list) for a port.

    Only ESTABLISHED connections are included in the list.
    """
    established = 0
    listening = 0
    conns: list[dict[str, object]] = []

    for entry in read_proc_net_tcp() + read_proc_net_tcp6():
        local_port = int(entry["local_port"])  # type: ignore[arg-type]
        st = int(entry["st"])  # type: ignore[arg-type]

        if local_port != port:
            continue

        if st == 0x0A:  # LISTEN
            listening += 1
        elif st == 0x01:  # ESTABLISHED
            established += 1
            conns.append(entry)

    return established, listening, conns


def get_connection_summary_from_text(
    tcp_text: str, tcp6_text: str, port: int
) -> tuple[int, int, list[dict[str, object]]]:
    """Parse remote /proc/net/tcp + tcp6 output and summarize connections for a port."""
    established = 0
    listening = 0
    conns: list[dict[str, object]] = []

    all_entries = parse_proc_output(tcp_text, ipv6=False) + parse_proc_output(tcp6_text, ipv6=True)

    for entry in all_entries:
        local_port = int(entry["local_port"])  # type: ignore[arg-type]
        st = int(entry["st"])  # type: ignore[arg-type]

        if local_port != port:
            continue

        if st == 0x0A:
            listening += 1
        elif st == 0x01:
            established += 1
            conns.append(entry)

    return established, listening, conns


def get_connection_summary_remote(
    tcp_text: str, tcp6_text: str, port: int
) -> tuple[int, int, list[dict[str, object]]]:
    """Alias for get_connection_summary_from_text."""
    return get_connection_summary_from_text(tcp_text, tcp6_text, port)