"""hookrunner command-line interface."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import httpx
import typer

from . import render
from .config import SchemeConfig, load_config
from .schemes import sign
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


def build_replay_headers(
    cfg: SchemeConfig, original: dict[str, str], body: bytes, timestamp: int
) -> dict[str, str]:
    """Build outgoing headers for a replay: original minus stale signature headers.

    The freshly computed signature (and any timestamp/nonce headers it carries)
    replace the captured ones; ``Host`` and ``Content-Length`` are dropped so the
    HTTP client recomputes them for the new request.

    Args:
        cfg: Scheme config to sign with.
        original: Headers from the captured request.
        body: Raw request body bytes.
        timestamp: Fresh Unix timestamp for schemes that carry one.

    Returns:
        The header mapping to send on the replayed request.
    """
    fresh = sign(cfg, body, timestamp)
    drop = {key.lower() for key in fresh} | {"host", "content-length"}
    result = {key: value for key, value in original.items() if key.lower() not in drop}
    result.update(fresh)
    return result


@app.command()
def replay(
    hook_id: Annotated[int, typer.Argument(metavar="ID", help="Hook id to replay.")],
    to: Annotated[str, typer.Option("--to", help="Target URL to POST to.")],
    secret_file: Annotated[Path, typer.Option("--secret-file", help="TOML config with secrets.")],
    db: DbOption = DEFAULT_DB,
) -> None:
    """Re-send a captured hook with a freshly recomputed, valid signature.

    Args:
        hook_id: The id of the hook to replay.
        to: Target URL to POST the hook to.
        secret_file: Path to the TOML config holding per-scheme secrets.
        db: Path to the SQLite capture database.

    Raises:
        Exit: With code 1 if the hook is missing, has no detected scheme, or the
            scheme is absent from the config.
    """
    with Store(db) as store:
        hook = store.get(hook_id)
    if hook is None:
        typer.echo(f"no hook with id {hook_id}", err=True)
        raise typer.Exit(1)
    if hook.scheme is None:
        typer.echo("hook has no detected scheme; cannot recompute a signature", err=True)
        raise typer.Exit(1)
    cfg = load_config(secret_file).get(hook.scheme)
    if cfg is None:
        typer.echo(f"scheme {hook.scheme!r} not present in {secret_file}", err=True)
        raise typer.Exit(1)

    headers = build_replay_headers(cfg, hook.headers, hook.body, int(time.time()))
    resp = httpx.post(to, content=hook.body, headers=headers)
    typer.echo(f"{resp.status_code} {resp.reason_phrase}")
    typer.echo(resp.text)
