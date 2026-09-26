"""SQLite persistence for captured webhooks."""

from __future__ import annotations

import json
import sqlite3
import threading
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
        # The receiver's ThreadingHTTPServer touches the store from per-request
        # threads, so the connection must not be pinned to its creating thread.
        # ponytail: one shared connection + a lock; move to a per-thread
        # connection pool only if capture throughput ever demands it.
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
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

    def insert(
        self,
        *,
        received_at: str,
        remote_addr: str,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        scheme: str | None,
        verified: bool | None,
        verify_error: str | None,
    ) -> int:
        """Persist a captured webhook and return its id.

        Args:
            received_at: ISO-8601 UTC capture time.
            remote_addr: Caller IP address.
            method: HTTP method.
            path: Request path.
            headers: Request headers (stored as JSON).
            body: Raw request body bytes (stored byte-exact as a BLOB).
            scheme: Detected scheme name, or None.
            verified: Verification result, or None if no scheme.
            verify_error: Failure reason, or None.

        Returns:
            The autoincrement id of the inserted row.
        """
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO hooks (received_at, remote_addr, method, path, headers, "
                "body, scheme, verified, verify_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    received_at,
                    remote_addr,
                    method,
                    path,
                    json.dumps(headers),
                    body,
                    scheme,
                    None if verified is None else int(verified),
                    verify_error,
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid or 0)

    def get(self, hook_id: int) -> Hook | None:
        """Fetch a single captured webhook by id.

        Args:
            hook_id: The row id to fetch.

        Returns:
            The matching Hook, or None if no row has that id.
        """
        with self._lock:
            row = self._conn.execute("SELECT * FROM hooks WHERE id = ?", (hook_id,)).fetchone()
        return None if row is None else self._row_to_hook(row)

    def list_hooks(self) -> list[Hook]:
        """Return all captured webhooks, most recent first.

        Returns:
            The list of Hook records ordered by descending id.
        """
        with self._lock:
            rows = self._conn.execute("SELECT * FROM hooks ORDER BY id DESC").fetchall()
        return [self._row_to_hook(row) for row in rows]

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
