"""Rich rendering for the ``list`` and ``show`` commands."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .store import Hook


def _verified_label(verified: bool | None) -> str:
    """Return a colored label for a verification result.

    Args:
        verified: Verification result, or None if unchecked.

    Returns:
        A rich-markup label string.
    """
    if verified is True:
        return "[green]verified[/green]"
    if verified is False:
        return "[red]FAILED[/red]"
    return "[dim]unverified[/dim]"


def render_list(hooks: list[Hook], console: Console | None = None) -> None:
    """Print a table of captured hooks, newest first.

    Args:
        hooks: Captured hook records.
        console: Rich console to print to (defaults to a new one).
    """
    console = console or Console()
    table = Table(title="captured webhooks")
    table.add_column("id", justify="right")
    table.add_column("received_at")
    table.add_column("scheme")
    table.add_column("path")
    table.add_column("status")
    for hook in hooks:
        table.add_row(
            str(hook.id),
            hook.received_at,
            hook.scheme or "[dim]none[/dim]",
            hook.path,
            _verified_label(hook.verified),
        )
    console.print(table)
