"""SSH remote client for ProxyWatch — connects to Linux VPS and executes commands."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import asyncssh


class RemoteClient:
    """Async SSH client for connecting to a remote Linux VPS.

    Uses asyncssh for non-blocking SSH operations that integrate with
    the Textual asyncio event loop.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.host: str = config.get("host", "")
        self.port: int = config.get("port", 22)
        self.user: str = config.get("user", "root")
        self.key_path: str | None = config.get("key_path")
        self.password: str | None = config.get("password")
        self._conn: asyncssh.SSHClientConnection | None = None
        self._connected: bool = False
        self._last_error: str = ""
        self._connect_time: float = 0.0
        self._reconnect_interval: float = 10.0
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def connect_time(self) -> float:
        return self._connect_time

    async def connect(self) -> bool:
        """Establish SSH connection to the remote VPS.

        Returns True on success, False on failure.
        """
        async with self._lock:
            if self._connected:
                return True

            try:
                kwargs: dict[str, Any] = {
                    "host": self.host,
                    "port": self.port,
                    "username": self.user,
                    "known_hosts": None,
                }

                if self.key_path:
                    kwargs["client_keys"] = [self.key_path]
                elif self.password:
                    kwargs["password"] = self.password
                else:
                    # Try default SSH keys
                    pass

                self._conn = await asyncio.wait_for(
                    asyncssh.connect(**kwargs),
                    timeout=15.0,
                )
                self._connected = True
                self._connect_time = time.time()
                self._last_error = ""
                return True

            except asyncio.TimeoutError:
                self._last_error = f"Connection to {self.host}:{self.port} timed out"
            except asyncssh.PermissionDenied:
                self._last_error = f"Permission denied for {self.user}@{self.host}"
            except asyncssh.Error as e:
                self._last_error = f"SSH error: {e}"
            except OSError as e:
                self._last_error = f"Network error: {e}"
            except Exception as e:
                self._last_error = f"Connection failed: {e}"

            self._connected = False
            self._conn = None
            return False

    async def disconnect(self) -> None:
        """Close the SSH connection."""
        async with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
            self._connected = False

    async def run(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        """Execute a command on the remote VPS.

        Args:
            command: Shell command to run.
            timeout: Timeout in seconds.

        Returns:
            Dict with keys: success (bool), stdout (str), stderr (str),
            exit_code (int), error (str).
        """
        result: dict[str, Any] = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": "",
        }

        if not self._connected or self._conn is None:
            result["error"] = "Not connected"
            return result

        try:
            proc = await asyncio.wait_for(
                self._conn.run(command),
                timeout=timeout,
            )
            result["success"] = proc.exit_status == 0
            result["exit_code"] = proc.exit_status
            result["stdout"] = proc.stdout.strip() if proc.stdout else ""
            result["stderr"] = proc.stderr.strip() if proc.stderr else ""
        except asyncio.TimeoutError:
            result["error"] = f"Command timed out: {command[:60]}..."
        except asyncssh.Error as e:
            result["error"] = f"SSH command error: {e}"
        except Exception as e:
            result["error"] = str(e)

        return result

    async def run_many(self, commands: dict[str, str], timeout: float = 30.0) -> dict[str, dict[str, Any]]:
        """Execute multiple commands concurrently.

        Args:
            commands: Dict mapping key -> command string.
            timeout: Timeout per command in seconds.

        Returns:
            Dict mapping key -> result dict (same format as run()).
        """
        tasks = {
            key: asyncio.create_task(self.run(cmd, timeout))
            for key, cmd in commands.items()
        }
        results: dict[str, dict[str, Any]] = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as e:
                results[key] = {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": str(e),
                }
        return results

    async def ensure_connected(self) -> bool:
        """Ensure the connection is alive, reconnecting if needed."""
        if self._connected and self._conn is not None:
            try:
                # Test the connection with a quick no-op
                await asyncio.wait_for(
                    self._conn.run("echo ok"),
                    timeout=5.0,
                )
                return True
            except Exception:
                self._connected = False
                self._conn = None

        return await self.connect()