# hookrunner

Local HMAC-signed webhook receiver + replay tool for backend dev.

Capture signed webhooks (Stripe, GitHub, generic HMAC) to SQLite, inspect them,
and replay against a local service with the signature still verifying.

## Install

```sh
pipx install hookrunner
```

## Usage

```sh
hookrunner serve --port 9000 --secret-file webhooks.toml   # receive + verify + store
hookrunner list                                            # list captured hooks
hookrunner show <id>                                       # inspect one
hookrunner replay <id> --to http://localhost:8000/webhook  # resend with fresh signature
```

## Stack

Python 3.11+ · stdlib `http.server` / `hmac` / `hashlib` / `sqlite3` · `typer` · `httpx` · `rich`. No web framework.

## License

MIT
