"""Splash screen with ASCII art logo for ProxyWatch."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static


SPLASH_ART = r"""
[bold cyan]
██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗
██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝
██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝
██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝
██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
[/bold cyan]
"""

SPLASH_BELOW = """
[bold white]ProxyWatch[/bold white]
[dim]Real-Time SOCKS5 Monitoring Dashboard[/dim]

[dim]v1.0.0[/dim]

[italic]Loading...[/italic]
"""


class SplashScreen(Screen):
    """Splash screen displayed while the dashboard initializes."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Skip"),
    ]

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                yield Static(SPLASH_ART, id="splash-art")
                yield Static(SPLASH_BELOW, id="splash-info")

    def on_mount(self) -> None:
        # Auto-dismiss after 2 seconds
        self.set_timer(2, self.dismiss_splash)

    def dismiss_splash(self) -> None:
        """Pop the splash screen and show the dashboard."""
        try:
            self.app.pop_screen()
        except Exception:
            pass