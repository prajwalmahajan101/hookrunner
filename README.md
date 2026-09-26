# hookrunner

[![CI](https://github.com/prajwalmahajan101/hookrunner/actions/workflows/ci.yml/badge.svg)](https://github.com/prajwalmahajan101/hookrunner/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Local HMAC-signed webhook receiver + replay tool for backend dev.

Capture signed webhooks (Stripe, GitHub, generic HMAC, custom) to SQLite, inspect
them, and replay against a local service with the signature still verifying.

## Install

```sh
pipx install hookrunner
```

## Configure

Copy the example config and fill in your secrets (`webhooks.toml` is gitignored):

```sh
cp webhooks.example.toml webhooks.toml
```

Built-in schemes (`stripe`, `github`, `optimo`) need only a `secret`. Custom
schemes are declared under `[custom.<name>]` with the full signature template —
see `webhooks.example.toml`.

## Usage

```sh
# 1. Receive: run a local server that verifies + stores every POST.
hookrunner serve --port 9000 --secret-file webhooks.toml

# 2. Inspect what came in.
hookrunner list
hookrunner show <id>

# 3. Replay to your local service with a fresh, valid signature.
hookrunner replay <id> --to http://localhost:8000/webhook
```

The receiver always responds `200` and records the verification result (it never
rejects), so failed-signature hooks are captured too. Bodies are stored
byte-exact, so replayed signatures verify.

### Signature schemes

| Scheme   | Header                 | Signed payload              |
|----------|------------------------|-----------------------------|
| `stripe` | `Stripe-Signature`     | `{timestamp}.{body}`        |
| `github` | `X-Hub-Signature-256`  | `{body}`                    |
| `optimo` | `X-Webhook-Signature`  | `{timestamp}.{nonce}.{body}`|
| custom   | configured header      | configured template         |

## Development

```sh
make install   # venv + deps + pre-commit hooks
make test      # pytest
make lint      # ruff
```

See `CLAUDE.md` for conventions and `docs/` for PRD / spec / roadmap.

## License

MIT — see `LICENSE`.
