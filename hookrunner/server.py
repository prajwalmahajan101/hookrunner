"""Local HTTP receiver that captures, verifies, and persists webhooks."""

from __future__ import annotations

from .config import SchemeConfig
from .schemes import OPTIMO_SIG_HEADER

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
