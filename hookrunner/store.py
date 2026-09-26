"""SQLite persistence for captured webhooks."""

from __future__ import annotations

from dataclasses import dataclass


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
