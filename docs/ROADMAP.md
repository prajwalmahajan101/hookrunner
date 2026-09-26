# hookrunner — Roadmap

## v1 — Core capture / verify / inspect / replay

The shippable tool. Everything in PRD/SPEC/REQUIREMENTS marked MUST.

- Receiver (`serve`) with SQLite capture.
- Four signature schemes: Stripe, GitHub, generic HMAC+nonce, custom TOML.
- Inspection: `list`, `show <id>`.
- Replay: `replay <id> --to <url>` with fresh signature.
- Hand-edited `webhooks.toml` + shipped `webhooks.example.toml`.
- `pipx`-installable, published to PyPI.
- 80%+ test coverage on verification paths.
- README with a 60-second capture → inspect → replay screencast.

**Definition of done:** all four schemes verify against real Stripe + GitHub test
events; clean `pipx install` on Linux/macOS/Windows.

## v2 — Config CLI

Manage `webhooks.toml` from the CLI instead of hand-editing.

- `hookrunner config add <scheme> --secret ...`
- `hookrunner config list` (secrets masked)
- `hookrunner config remove <scheme>`
- TOML read + write with validation.

## v3 — TUI (stretch)

- `hookrunner tui` (Textual): live webhook stream + side panel for inspecting
  payloads, if the config CLI proves insufficient.

## Backlog (unscheduled)

- HAR-style export of captured hooks.
- `hookrunner test <url>` — synthetic webhook generation for load testing.
- VS Code extension running hookrunner in a status-bar item.
- Stale-timestamp rejection mode (opt-in `--reject-invalid`).
