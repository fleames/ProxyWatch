"""Human-readable formatting utilities for bytes, durations, and rates."""

from __future__ import annotations


def fmt_bytes(size: int, precision: int = 1) -> str:
    """Format a byte count into a human-readable string.

    Args:
        size: Number of bytes.
        precision: Decimal places for the formatted value.

    Returns:
        String like "1.2 KB" or "37.1 GB".
    """
    if size < 0:
        size = 0

    if size < 1024:
        return f"{size} B"

    for unit in ("KB", "MB", "GB", "TB", "PB"):
        size /= 1024.0
        if size < 1024 or unit == "PB":
            return f"{size:.{precision}f} {unit}"

    return f"{size:.{precision}f} PB"


def fmt_bits_per_second(bps: float, precision: int = 1) -> str:
    """Format bits-per-second into a human-readable rate string.

    Args:
        bps: Bits per second.
        precision: Decimal places.

    Returns:
        String like "12.3 Mbps" or "4.1 Kbps".
    """
    if bps < 0:
        bps = 0.0

    for unit in ("bps", "Kbps", "Mbps", "Gbps", "Tbps"):
        if bps < 1000 or unit == "Tbps":
            return f"{bps:.{precision}f} {unit}"
        bps /= 1000.0

    return f"{bps:.{precision}f} Tbps"


def fmt_duration(seconds: int) -> str:
    """Format a duration in seconds to a compact human-readable string.

    Args:
        seconds: Number of seconds.

    Returns:
        String like "3d 12h 5m" or "45s".
    """
    if seconds < 0:
        seconds = 0

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts or secs:
        parts.append(f"{secs}s")

    return " ".join(parts)


def fmt_duration_short(seconds: int) -> str:
    """Format a duration as HH:MM:SS."""
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def fmt_percentage(value: float, precision: int = 1) -> str:
    """Format a fraction (0.0–1.0) as a percentage string.

    Args:
        value: Fraction between 0 and 1.
        precision: Decimal places.

    Returns:
        String like "34.5%".
    """
    return f"{value * 100:.{precision}f}%"


def fmt_number(value: int) -> str:
    """Format an integer with thousands separators.

    Returns:
        String like "1,234,567".
    """
    return f"{value:,}"


def fmt_uptime(seconds: int) -> str:
    """Format system uptime as a compact string."""
    return fmt_duration(seconds)