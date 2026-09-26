"""hookrunner command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import render
from .config import load_config
from .server import serve as run_server
from .store import Store

app = typer.Typer(
    help="Local HMAC-signed webhook receiver + replay tool.",
    no_args_is_help=True,
    add_completion=False,
)

DEFAULT_DB = Path("hookrunner.db")

DbOption = Annotated[Path, typer.Option("--db", help="SQLite capture file.")]


@app.command()
def serve(
    secret_file: Annotated[Path, typer.Option("--secret-file", help="TOML config with secrets.")],
    port: Annotated[int, typer.Option("--port", help="Port to listen on.")] = 9000,
    db: DbOption = DEFAULT_DB,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
) -> None:
    """Run the receiver: capture, verify, and persist incoming webhooks.

    Args:
        secret_file: Path to the TOML config holding per-scheme secrets.
        port: TCP port to listen on.
        db: Path to the SQLite capture database.
        host: Interface to bind.
    """
    schemes = load_config(secret_file)
    store = Store(db)
    typer.echo(f"listening on http://{host}:{port}  (db={db})")
    run_server(port, schemes, store, host)


@app.command("list")
def list_(db: DbOption = DEFAULT_DB) -> None:
    """List captured hooks, newest first.

    Args:
        db: Path to the SQLite capture database.
    """
    with Store(db) as store:
        render.render_list(store.list_hooks())


@app.command()
def show(
    hook_id: Annotated[int, typer.Argument(metavar="ID", help="Hook id to inspect.")],
    db: DbOption = DEFAULT_DB,
) -> None:
    """Pretty-print a single captured hook.

    Args:
        hook_id: The id of the hook to show.
        db: Path to the SQLite capture database.

    Raises:
        Exit: With code 1 if no hook has the given id.
    """
    with Store(db) as store:
        hook = store.get(hook_id)
    if hook is None:
        typer.echo(f"no hook with id {hook_id}", err=True)
        raise typer.Exit(1)
    render.render_show(hook)
