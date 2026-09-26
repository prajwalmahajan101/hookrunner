"""Signature verification and (re)signing for each supported webhook scheme.

Every scheme exposes the same pair of operations via :func:`verify` and
:func:`sign`, dispatched on the :class:`~hookrunner.config.SchemeConfig`. Built-in
schemes (``stripe``, ``github``, ``optimo``) have fixed header names and layouts;
custom schemes are driven entirely by their config template. All comparisons use
:func:`hmac.compare_digest`, and the request body is treated as raw bytes so the
signed message is always byte-exact.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from .config import SchemeConfig

# Fixed header names for the generic HMAC+nonce (Optimo-style) scheme.
OPTIMO_SIG_HEADER = "X-Webhook-Signature"
OPTIMO_TIMESTAMP_HEADER = "X-Webhook-Timestamp"
OPTIMO_NONCE_HEADER = "X-Webhook-Nonce"
OPTIMO_TEMPLATE = "{timestamp}.{nonce}.{body}"

_ALGOS = {"sha256": hashlib.sha256, "sha1": hashlib.sha1}


class VerifyError(Exception):
    """Raised when a signature is missing, malformed, or does not match."""


def verify(cfg: SchemeConfig, headers: dict[str, str], body: bytes) -> None:
    """Verify the signature on a received request.

    Delegates to the per-scheme checker, which raises
    :class:`VerifyError` if the required header is absent, malformed, or the
    computed signature does not match the provided one.

    Args:
        cfg: Resolved configuration for the scheme to check against.
        headers: Request headers (looked up case-insensitively).
        body: Raw request body bytes.
    """
    if cfg.builtin and cfg.name == "stripe":
        _stripe_verify(cfg, headers, body)
    elif cfg.builtin and cfg.name == "github":
        _github_verify(cfg, headers, body)
    elif cfg.builtin and cfg.name == "optimo":
        _optimo_verify(cfg, headers, body)
    else:
        _custom_verify(cfg, headers, body)


def sign(cfg: SchemeConfig, body: bytes, timestamp: int) -> dict[str, str]:
    """Compute fresh signature headers for a replayed request.

    Args:
        cfg: Resolved configuration for the scheme to sign with.
        body: Raw request body bytes to sign.
        timestamp: Unix timestamp to embed in schemes that carry one.

    Returns:
        Header name to value mapping to set on the outgoing request.
    """
    if cfg.builtin and cfg.name == "stripe":
        return _stripe_sign(cfg, body, timestamp)
    if cfg.builtin and cfg.name == "github":
        return _github_sign(cfg, body)
    if cfg.builtin and cfg.name == "optimo":
        return _optimo_sign(cfg, body, timestamp)
    return _custom_sign(cfg, body, timestamp)


# --- shared helpers -------------------------------------------------------


def _get(headers: dict[str, str], name: str) -> str:
    """Return a request header value by case-insensitive name.

    Args:
        headers: Request headers.
        name: Header name to fetch.

    Returns:
        The header value.

    Raises:
        VerifyError: If the header is not present.
    """
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    raise VerifyError(f"missing header {name!r}")


def _render(template: str, body: bytes, timestamp: int | None, nonce: str | None) -> bytes:
    """Render a signed-payload template into raw bytes, keeping the body exact.

    Args:
        template: Template string with ``{body}``/``{timestamp}``/``{nonce}``.
        body: Raw request body bytes, substituted for ``{body}`` verbatim.
        timestamp: Value for ``{timestamp}``, or None if unused.
        nonce: Value for ``{nonce}``, or None if unused.

    Returns:
        The rendered message as bytes.
    """
    text = template
    if timestamp is not None:
        text = text.replace("{timestamp}", str(timestamp))
    if nonce is not None:
        text = text.replace("{nonce}", nonce)
    segments = text.split("{body}")
    return body.join(segment.encode("utf-8") for segment in segments)


def _digest(secret: str, algo: str, message: bytes, encoding: str) -> str:
    """Compute an encoded HMAC digest.

    Args:
        secret: Shared secret.
        algo: Digest algorithm name (``sha256`` or ``sha1``).
        message: Message bytes to sign.
        encoding: Output encoding (``hex`` or ``base64``).

    Returns:
        The encoded digest string.
    """
    mac = hmac.new(secret.encode("utf-8"), message, _ALGOS[algo]).digest()
    if encoding == "base64":
        return base64.b64encode(mac).decode("ascii")
    return mac.hex()


def _check(expected: str, provided: str) -> None:
    """Constant-time compare an expected signature against a provided one.

    Args:
        expected: Locally computed signature.
        provided: Signature taken from the request.

    Raises:
        VerifyError: If the two do not match.
    """
    if not hmac.compare_digest(expected, provided):
        raise VerifyError("signature mismatch")


# --- stripe ---------------------------------------------------------------


def _stripe_parse(raw: str) -> tuple[str, list[str]]:
    """Parse a ``Stripe-Signature`` header into its timestamp and v1 signatures.

    Args:
        raw: The raw header value (``t=...,v1=...,v1=...``).

    Returns:
        The timestamp string and the list of ``v1`` signature values.

    Raises:
        VerifyError: If no timestamp or no ``v1`` signature is present.
    """
    timestamp = ""
    v1: list[str] = []
    for item in raw.split(","):
        key, _, value = item.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            v1.append(value)
    if not timestamp or not v1:
        raise VerifyError("malformed Stripe-Signature header")
    return timestamp, v1


def _stripe_verify(cfg: SchemeConfig, headers: dict[str, str], body: bytes) -> None:
    """Verify a Stripe signature.

    Args:
        cfg: Stripe scheme config.
        headers: Request headers.
        body: Raw request body.

    Raises:
        VerifyError: If the header is malformed or no ``v1`` value matches.
    """
    timestamp, signatures = _stripe_parse(_get(headers, "Stripe-Signature"))
    message = _render("{timestamp}.{body}", body, int(timestamp), None)
    expected = _digest(cfg.secret, "sha256", message, "hex")
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise VerifyError("signature mismatch")


def _stripe_sign(cfg: SchemeConfig, body: bytes, timestamp: int) -> dict[str, str]:
    """Compute a fresh Stripe-Signature header.

    Args:
        cfg: Stripe scheme config.
        body: Raw request body.
        timestamp: Unix timestamp to embed.

    Returns:
        The Stripe-Signature header mapping.
    """
    sig = _digest(cfg.secret, "sha256", _render("{timestamp}.{body}", body, timestamp, None), "hex")
    return {"Stripe-Signature": f"t={timestamp},v1={sig}"}


# --- github ---------------------------------------------------------------


def _github_verify(cfg: SchemeConfig, headers: dict[str, str], body: bytes) -> None:
    """Verify a GitHub ``X-Hub-Signature-256`` signature.

    Raises :class:`VerifyError` (via the header lookup / comparison helpers) if
    the header is missing or the signature does not match.

    Args:
        cfg: GitHub scheme config.
        headers: Request headers.
        body: Raw request body.
    """
    provided = _get(headers, "X-Hub-Signature-256")
    expected = "sha256=" + _digest(cfg.secret, "sha256", body, "hex")
    _check(expected, provided)


def _github_sign(cfg: SchemeConfig, body: bytes) -> dict[str, str]:
    """Compute a fresh GitHub signature header.

    Args:
        cfg: GitHub scheme config.
        body: Raw request body.

    Returns:
        The X-Hub-Signature-256 header mapping.
    """
    return {"X-Hub-Signature-256": "sha256=" + _digest(cfg.secret, "sha256", body, "hex")}


# --- optimo (generic HMAC+nonce) ------------------------------------------


def _optimo_verify(cfg: SchemeConfig, headers: dict[str, str], body: bytes) -> None:
    """Verify a generic HMAC+nonce (Optimo-style) signature.

    Raises :class:`VerifyError` (via the header lookup / comparison helpers) if a
    required header is missing or the signature mismatches.

    Args:
        cfg: Optimo scheme config.
        headers: Request headers.
        body: Raw request body.
    """
    provided = _get(headers, OPTIMO_SIG_HEADER)
    timestamp = _get(headers, OPTIMO_TIMESTAMP_HEADER)
    nonce = _get(headers, OPTIMO_NONCE_HEADER)
    message = _render(OPTIMO_TEMPLATE, body, int(timestamp), nonce)
    _check(_digest(cfg.secret, "sha256", message, "hex"), provided)


def _optimo_sign(cfg: SchemeConfig, body: bytes, timestamp: int) -> dict[str, str]:
    """Compute fresh Optimo signature, timestamp, and nonce headers.

    Args:
        cfg: Optimo scheme config.
        body: Raw request body.
        timestamp: Unix timestamp to embed.

    Returns:
        Mapping of the signature, timestamp, and nonce headers.
    """
    nonce = secrets.token_hex(16)
    message = _render(OPTIMO_TEMPLATE, body, timestamp, nonce)
    return {
        OPTIMO_SIG_HEADER: _digest(cfg.secret, "sha256", message, "hex"),
        OPTIMO_TIMESTAMP_HEADER: str(timestamp),
        OPTIMO_NONCE_HEADER: nonce,
    }


# --- custom (template-driven) ---------------------------------------------


def _custom_verify(cfg: SchemeConfig, headers: dict[str, str], body: bytes) -> None:
    """Verify a custom, template-driven signature.

    Raises :class:`VerifyError` (via the header lookup / comparison helpers) if the
    signature header is missing or does not match.

    Args:
        cfg: Custom scheme config.
        headers: Request headers.
        body: Raw request body.
    """
    assert cfg.header is not None  # guaranteed for custom schemes by config loader
    provided = _get(headers, cfg.header)
    timestamp = int(_get(headers, cfg.timestamp_header)) if cfg.timestamp_header else None
    nonce = _get(headers, cfg.nonce_header) if cfg.nonce_header else None
    message = _render(cfg.signed_payload, body, timestamp, nonce)
    expected = cfg.prefix + _digest(cfg.secret, cfg.algo, message, cfg.encoding)
    _check(expected, provided)


def _custom_sign(cfg: SchemeConfig, body: bytes, timestamp: int) -> dict[str, str]:
    """Compute fresh headers for a custom, template-driven scheme.

    Args:
        cfg: Custom scheme config.
        body: Raw request body.
        timestamp: Unix timestamp to embed if the template uses ``{timestamp}``.

    Returns:
        Mapping of the signature header (and timestamp/nonce headers when used).
    """
    assert cfg.header is not None  # guaranteed for custom schemes by config loader
    uses_ts = "{timestamp}" in cfg.signed_payload
    uses_nonce = "{nonce}" in cfg.signed_payload
    nonce = secrets.token_hex(16) if uses_nonce else None
    message = _render(cfg.signed_payload, body, timestamp if uses_ts else None, nonce)
    result = {cfg.header: cfg.prefix + _digest(cfg.secret, cfg.algo, message, cfg.encoding)}
    if uses_ts and cfg.timestamp_header:
        result[cfg.timestamp_header] = str(timestamp)
    if uses_nonce and cfg.nonce_header and nonce is not None:
        result[cfg.nonce_header] = nonce
    return result
