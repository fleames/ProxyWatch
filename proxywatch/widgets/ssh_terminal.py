"""Full SSH terminal widget — interactive VPS command shell."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import (
    Static,
    Input,
    RichLog,
)

if TYPE_CHECKING:
    from proxywatch.remote import RemoteClient


class SSHTerminalPanel(Container):
    """Interactive SSH terminal for full VPS management.

    Provides a command input and scrollable output log. Commands are executed
    on the remote VPS via the SSH connection.
    """

    def __init__(self, remote_client: "RemoteClient | None" = None) -> None:
        super().__init__()
        self._remote = remote_client
        self._history: list[str] = []
        self._history_idx: int = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="ssh-terminal-container"):
            yield Static(
                "[bold cyan]⚡ SSH TERMINAL[/bold cyan] [dim]— Full VPS Control[/dim]",
                id="ssh-terminal-title",
            )
            yield RichLog(
                id="ssh-terminal-output",
                highlight=True,
                markup=True,
                max_lines=2000,
                auto_scroll=True,
            )
            with Container(id="ssh-terminal-input-row"):
                yield Static("[bold green]root@vps[/]:[bold blue]~[/]$", id="ssh-prompt")
                yield Input(
                    placeholder="Type command and press Enter...",
                    id="ssh-terminal-input",
                )

    def on_mount(self) -> None:
        """Initialize terminal."""
        output = self.query_one("#ssh-terminal-output", RichLog)
        output.write("[dim]ProxyWatch SSH Terminal v2.0[/dim]")
        output.write("[dim]Type 'help' for available commands, 'exit' to close.[/dim]")

        if self._remote and self._remote.connected:
            host = self._remote.host
            output.write(f"[green]✓ Connected to {host}[/green]")
            prompt = self.query_one("#ssh-prompt", Static)
            prompt.update(f"[bold green]root@{host}[/]:[bold blue]~[/]$")
        else:
            output.write("[red]✗ Not connected to remote VPS[/red]")

        self._focus_input()

    def _focus_input(self) -> None:
        """Focus the command input."""
        try:
            inp = self.query_one("#ssh-terminal-input", Input)
            inp.focus()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command = event.value.strip()
        if not command:
            return

        output = self.query_one("#ssh-terminal-output", RichLog)
        inp = self.query_one("#ssh-terminal-input", Input)

        # Clear input
        inp.value = ""

        # Add to history
        self._history.append(command)
        self._history_idx = len(self._history)

        # Echo command
        host = self._remote.host if self._remote else "vps"
        output.write(f"[bold green]root@{host}[/]:[bold blue]~[/]$ [white]{command}[/white]")

        # Handle built-in commands
        if command.lower() in ("exit", "quit"):
            output.write("[dim]Use Ctrl+Q to close the dashboard[/dim]")
            self._focus_input()
            return

        if command.lower() == "help":
            self._show_help(output)
            self._focus_input()
            return

        if command.lower() == "clear":
            output.clear()
            self._focus_input()
            return

        if command.lower() == "history":
            for i, cmd in enumerate(self._history[-50:], 1):
                output.write(f"[dim]{i:4d}  {cmd}[/dim]")
            self._focus_input()
            return

        # Execute remote command
        if self._remote and self._remote.connected:
            output.write("[dim]Running...[/dim]")
            result = await self._remote.run(command, timeout=30.0)

            if result["success"]:
                stdout = result["stdout"]
                if stdout:
                    for line in stdout.splitlines():
                        output.write(f"[white]{line}[/white]")
                else:
                    output.write("[dim](no output)[/dim]")
            else:
                error = result.get("error") or result.get("stderr") or "Command failed"
                output.write(f"[red]{error}[/red]")
        else:
            output.write("[red]Not connected to remote VPS. Check config.yaml remote settings.[/red]")

        self._focus_input()

    def _show_help(self, output: RichLog) -> None:
        """Display help text."""
        output.write("""
[bold cyan]ProxyWatch SSH Terminal — Available Commands[/bold cyan]
[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]
  [bold]help[/bold]      Show this help
  [bold]clear[/bold]     Clear terminal output
  [bold]history[/bold]   Show command history
  [bold]exit[/bold]      Exit terminal mode

[bold cyan]Common VPS Commands[/bold cyan]
  [bold]docker ps[/bold]              List running containers
  [bold]docker stats --no-stream[/bold] Container resource usage
  [bold]docker logs socks5[/bold]     View proxy logs
  [bold]htop[/bold]                   Interactive process viewer
  [bold]systemctl status[/bold]       Check service status
  [bold]df -h[/bold]                  Disk usage
  [bold]free -h[/bold]                Memory usage
  [bold]uptime[/bold]                 System uptime
  [bold]ss -tnp[/bold]                Active connections
  [bold]nethogs[/bold]                Per-process bandwidth
  [bold]journalctl -f[/bold]          Follow system logs

[dim]Any shell command can be executed directly.[/dim]
""")

    async def refresh_connection(self) -> None:
        """Refresh connection status display."""
        output = self.query_one("#ssh-terminal-output", RichLog)
        prompt = self.query_one("#ssh-prompt", Static)

        if self._remote and self._remote.connected:
            host = self._remote.host
            prompt.update(f"[bold green]root@{host}[/]:[bold blue]~[/]$")
        else:
            prompt.update("[bold red]root@vps[/]:[bold blue]~[/]$")