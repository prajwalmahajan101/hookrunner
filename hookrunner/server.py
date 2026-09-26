"""Local HTTP receiver that captures, verifies, and persists webhooks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

from .config import SchemeConfig
from .schemes import OPTIMO_SIG_HEADER, VerifyError, verify
from .store import Store

# Built-in schemes in detection-precedence order, paired with the (lowercased)
# header whose presence identifies them.
_BUILTIN_HEADERS = (
    ("stripe", "stripe-signature"),
    ("github", "x-hub-signature-256"),
    ("optimo", OPTIMO_SIG_HEADER.lower()),
)


def detect_scheme(schemes: dict[str, SchemeConfig], headers: dict[str, str]) -> SchemeConfig | None:
    """Pick the configured scheme whose signature header is present.

    Built-in schemes take precedence in a fixed order; custom schemes are matched
    on their configured header afterwards.

    Args:
        schemes: Configured schemes keyed by name.
        headers: Request headers.

    Returns:
        The matching scheme config, or None if no configured scheme's header is present.
    """
    present = {key.lower() for key in headers}
    for name, header in _BUILTIN_HEADERS:
        if name in schemes and header in present:
            return schemes[name]
    for cfg in schemes.values():
        if not cfg.builtin and cfg.header and cfg.header.lower() in present:
            return cfg
    return None


class HookServer(ThreadingHTTPServer):
    """Threaded HTTP server carrying the scheme config and capture store."""

    def __init__(
        self, address: tuple[str, int], schemes: dict[str, SchemeConfig], store: Store
    ) -> None:
        """Create the server.

        Args:
            address: Host/port tuple to bind.
            schemes: Configured schemes keyed by name.
            store: Capture store to persist received hooks into.
        """
        super().__init__(address, _Handler)
        self.schemes = schemes
        self.store = store


class _Handler(BaseHTTPRequestHandler):
    """Accepts any POST, verifies its signature, persists it, and returns 200."""

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        """Capture one POSTed webhook: verify, persist, and always answer 200."""
        server = cast(HookServer, self.server)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        headers = {key: value for key, value in self.headers.items()}

        scheme = detect_scheme(server.schemes, headers)
        scheme_name: str | None = None
        verified: bool | None = None
        verify_error: str | None = None
        if scheme is not None:
            scheme_name = scheme.name
            try:
                verify(scheme, headers, body)
                verified = True
            except VerifyError as exc:
                verified = False
                verify_error = str(exc)

        hook_id = server.store.insert(
            received_at=datetime.now(UTC).isoformat(),
            remote_addr=self.client_address[0],
            method="POST",
            path=self.path,
            headers=headers,
            body=body,
            scheme=scheme_name,
            verified=verified,
            verify_error=verify_error,
        )

        payload = json.dumps({"id": hook_id, "verified": verified}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request stderr logging.

        Args:
            format: Printf-style format string (ignored).
            args: Format arguments (ignored).
        """


def serve(
    port: int, schemes: dict[str, SchemeConfig], store: Store, host: str = "127.0.0.1"
) -> None:
    """Run the receiver until interrupted.

    Args:
        port: TCP port to listen on.
        schemes: Configured schemes keyed by name.
        store: Capture store to persist received hooks into.
        host: Interface to bind (defaults to loopback).
    """
    server = HookServer((host, port), schemes, store)
    try:
        server.serve_forever()
    finally:
        server.server_close()
