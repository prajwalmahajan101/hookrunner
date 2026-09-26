"""Send one test webhook per scheme to a running hookrunner receiver.

Usage: python scripts/send_hooks.py http://127.0.0.1:9400

Signatures are built with hookrunner's own signer, so a receiver configured with
the same secret ("demo") verifies them. One deliberately tampered hook is sent
last to show a captured-but-failed verification.
"""

from __future__ import annotations

import sys
import time

import httpx

from hookrunner.config import SchemeConfig
from hookrunner.schemes import sign

SECRET = "demo"


def _post(base: str, headers: dict[str, str], body: bytes, label: str) -> None:
    resp = httpx.post(f"{base}/webhook", content=body, headers=headers)
    print(f"{label:16} -> {resp.status_code} {resp.json()}")


def _wait(base: str) -> None:
    for _ in range(50):
        try:
            httpx.get(base, timeout=0.3)
            return
        except httpx.HTTPError:
            time.sleep(0.1)


def main() -> None:
    base = sys.argv[1]
    _wait(base)
    now = int(time.time())

    github = SchemeConfig(name="github", secret=SECRET, builtin=True)
    stripe = SchemeConfig(name="stripe", secret=SECRET, builtin=True)
    optimo = SchemeConfig(name="optimo", secret=SECRET, builtin=True)
    custom = SchemeConfig(
        name="partnerx",
        secret=SECRET,
        header="X-Partner-Signature",
        signed_payload="{timestamp}.{body}",
        prefix="sha256=",
        timestamp_header="X-Partner-Timestamp",
    )

    _post(base, sign(github, b'{"scheme":"github"}', now), b'{"scheme":"github"}', "github")
    _post(base, sign(stripe, b'{"scheme":"stripe"}', now), b'{"scheme":"stripe"}', "stripe")
    _post(base, sign(optimo, b'{"scheme":"optimo"}', now), b'{"scheme":"optimo"}', "optimo")
    _post(base, sign(custom, b'{"scheme":"custom"}', now), b'{"scheme":"custom"}', "custom")

    body = b'{"scheme":"github"}'
    _post(base, sign(github, body, now), body + b"TAMPERED", "tampered-github")


if __name__ == "__main__":
    main()
