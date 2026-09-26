"""SQLite persistence for captured webhooks."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hooks (
    id           INTEGER PRIMARY KEY,
    received_at  TEXT    NOT NULL,
    remote_addr  TEXT    NOT NULL,
    method       TEXT    NOT NULL,
    path         TEXT    NOT NULL,
    headers      TEXT    NOT NULL,
    body         BLOB    NOT NULL,
    scheme       TEXT,
    verified     INTEGER,
    verify_error TEXT
)
"""


@dataclass
class Hook:
    """A single captured webhook record.

    Attributes:
        id: Autoincrement row id.
        received_at: ISO-8601 UTC capture time.
        remote_addr: Caller IP address.
        method: HTTP method (always POST in v1).
        path: Request path.
        headers: Request headers.
        body: Raw request body bytes (stored byte-exact).
        scheme: Detected scheme name, or None if none matched.
        verified: True/False verification result, or None if no scheme.
        verify_error: Failure reason, or None when verified or unchecked.
    """

    id: int
    received_at: str
    remote_addr: str
    method: str
    path: str
    headers: dict[str, str]
    body: bytes
    scheme: str | None
    verified: bool | None
    verify_error: str | None


class Store:
    """SQLite-backed repository for captured webhooks."""

    def __init__(self, path: str | Path) -> None:
        """Open the database and ensure the schema exists.

        Args:
            path: Path to the SQLite database file.
        """
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Store:
        """Enter a context manager.

        Returns:
            This store instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the connection on context-manager exit.

        Args:
            exc_type: Exception type, if one was raised.
            exc: Exception instance, if one was raised.
            tb: Traceback, if an exception was raised.
        """
        self.close()

    @staticmethod
    def _row_to_hook(row: sqlite3.Row) -> Hook:
        """Map a database row to a Hook.

        Args:
            row: A row from the ``hooks`` table.

        Returns:
            The reconstructed Hook record.
        """
        verified = row["verified"]
        return Hook(
            id=row["id"],
            received_at=row["received_at"],
            remote_addr=row["remote_addr"],
            method=row["method"],
            path=row["path"],
            headers=json.loads(row["headers"]),
            body=row["body"],
            scheme=row["scheme"],
            verified=None if verified is None else bool(verified),
            verify_error=row["verify_error"],
        )
