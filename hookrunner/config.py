"""Load and validate signature-scheme configuration from a TOML file.

The config file (``webhooks.toml``) holds one secret per scheme. Built-in schemes
(``stripe``, ``github``, ``optimo``) need only a ``secret``; their header, algo,
signed-payload template, encoding, and prefix are fixed in :mod:`hookrunner.schemes`.
Custom schemes are declared under a ``[custom.<name>]`` table and carry the full
template so an arbitrary HMAC scheme can be verified and replayed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

BUILTIN_SCHEMES = frozenset({"stripe", "github", "optimo"})
ALGOS = frozenset({"sha256", "sha1"})
ENCODINGS = frozenset({"hex", "base64"})


class ConfigError(Exception):
    """Raised when the TOML config is malformed or fails validation."""


@dataclass(frozen=True)
class SchemeConfig:
    """Resolved configuration for a single signature scheme.

    Attributes:
        name: Scheme identifier (e.g. ``stripe`` or a custom name like ``partnerx``).
        secret: Shared secret used to compute the HMAC.
        builtin: True for the fixed built-in schemes; False for custom schemes.
        header: Signature header name. None for built-ins (fixed in schemes.py).
        algo: HMAC digest algorithm, one of :data:`ALGOS`.
        signed_payload: Template for the signed bytes; placeholders ``{body}``,
            ``{timestamp}``, ``{nonce}``.
        encoding: Digest encoding, one of :data:`ENCODINGS`.
        prefix: String prepended to the encoded digest in the header value.
    """

    name: str
    secret: str
    builtin: bool = False
    header: str | None = None
    algo: str = "sha256"
    signed_payload: str = "{body}"
    encoding: str = "hex"
    prefix: str = ""


def load_config(path: str | Path) -> dict[str, SchemeConfig]:
    """Parse and validate a webhooks TOML config into scheme objects.

    Args:
        path: Path to the TOML config file.

    Returns:
        Mapping of scheme name to its resolved :class:`SchemeConfig`.

    Raises:
        ConfigError: If the file is missing, not valid TOML, contains an unknown
            top-level table, or a scheme table fails validation.
    """
    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    schemes: dict[str, SchemeConfig] = {}

    for key, value in raw.items():
        if key == "custom":
            _load_custom(value, schemes)
        elif key in BUILTIN_SCHEMES:
            schemes[key] = _load_builtin(key, value)
        else:
            raise ConfigError(
                f"unknown top-level table [{key}]; expected one of "
                f"{sorted(BUILTIN_SCHEMES)} or [custom.<name>]"
            )

    return schemes


def _load_builtin(name: str, table: object) -> SchemeConfig:
    """Build a SchemeConfig for a built-in scheme.

    Args:
        name: Built-in scheme name.
        table: The TOML table for the scheme; must be a mapping with a ``secret``.

    Returns:
        The resolved scheme configuration.

    Raises:
        ConfigError: If the table is not a mapping or has no non-empty ``secret``.
    """
    if not isinstance(table, dict):
        raise ConfigError(f"[{name}] must be a table")
    secret = table.get("secret")
    if not isinstance(secret, str) or not secret:
        raise ConfigError(f"[{name}] requires a non-empty string 'secret'")
    return SchemeConfig(name=name, secret=secret, builtin=True)


def _load_custom(table: object, schemes: dict[str, SchemeConfig]) -> None:
    """Parse the ``[custom.*]`` tables and add them to the scheme map.

    Args:
        table: The value of the top-level ``custom`` key; a mapping of custom
            scheme name to its definition table.
        schemes: Accumulator mutated in place with the parsed custom schemes.

    Raises:
        ConfigError: If ``custom`` is not a table, a custom name collides with a
            built-in, or a definition is missing/invalid.
    """
    if not isinstance(table, dict):
        raise ConfigError("[custom] must be a table of [custom.<name>] entries")
    for name, definition in table.items():
        if name in BUILTIN_SCHEMES:
            raise ConfigError(f"custom scheme '{name}' collides with a built-in name")
        if not isinstance(definition, dict):
            raise ConfigError(f"[custom.{name}] must be a table")
        schemes[name] = _build_custom(name, definition)


def _build_custom(name: str, d: dict[str, object]) -> SchemeConfig:
    """Validate one custom-scheme definition and build its SchemeConfig.

    Args:
        name: Custom scheme name.
        d: The ``[custom.<name>]`` definition table.

    Returns:
        The resolved scheme configuration.

    Raises:
        ConfigError: If a required field is missing, or ``algo``/``encoding`` is
            not one of the supported values.
    """
    header = _require_str(name, d, "header")
    secret = _require_str(name, d, "secret")
    signed_payload = d.get("signed_payload", "{body}")
    algo = d.get("algo", "sha256")
    encoding = d.get("encoding", "hex")
    prefix = d.get("prefix", "")

    for field, value, allowed in (
        ("algo", algo, ALGOS),
        ("encoding", encoding, ENCODINGS),
    ):
        if value not in allowed:
            raise ConfigError(
                f"[custom.{name}] {field}='{value}' invalid; expected one of {sorted(allowed)}"
            )
    for field, value in (("signed_payload", signed_payload), ("prefix", prefix)):
        if not isinstance(value, str):
            raise ConfigError(f"[custom.{name}] {field} must be a string")

    return SchemeConfig(
        name=name,
        secret=secret,
        builtin=False,
        header=header,
        algo=str(algo),
        signed_payload=str(signed_payload),
        encoding=str(encoding),
        prefix=str(prefix),
    )


def _require_str(name: str, d: dict[str, object], field: str) -> str:
    """Return a required non-empty string field from a custom definition.

    Args:
        name: Custom scheme name, for error messages.
        d: The definition table.
        field: Field name to fetch.

    Returns:
        The field's string value.

    Raises:
        ConfigError: If the field is absent, not a string, or empty.
    """
    value = d.get(field)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"[custom.{name}] requires a non-empty string '{field}'")
    return value
