# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-26

Initial release — capture, verify, inspect, and replay HMAC-signed webhooks locally.

### Added

- `serve` — local HTTP receiver that verifies signatures and persists every
  request to SQLite; always returns 200 and records the verification result.
- Signature schemes: **Stripe** (`Stripe-Signature`), **GitHub**
  (`X-Hub-Signature-256`), **Optimo** (generic HMAC+nonce), and TOML-defined
  **custom** schemes (header, algo, signed-payload template, encoding, prefix).
  All comparisons use `hmac.compare_digest`; bodies stored byte-exact.
- `list` — rich table of captured hooks.
- `show <id>` — pretty-printed headers + JSON-highlighted body + verification status.
- `replay <id> --to <url>` — re-send a captured hook with a fresh timestamp and
  recomputed, valid signature.
- Config via `webhooks.toml` (`webhooks.example.toml` reference shipped).
- Packaging: `pipx`/PyPI-ready (hatchling), `hookrunner` console entry point.
- CI: ruff, mypy --strict, pydocstyle + darglint, pytest on Python 3.11–3.13,
  dependency-drift check, pip-audit; 80% coverage gate on the verification paths.

[Unreleased]: https://github.com/prajwalmahajan101/hookrunner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/prajwalmahajan101/hookrunner/releases/tag/v0.1.0
