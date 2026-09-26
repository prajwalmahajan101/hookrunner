# CLAUDE.md — hookrunner

Local HMAC-signed webhook receiver + replay tool. Capture signed webhooks to
SQLite, inspect them, and replay against a local service with the signature still
verifying. CLI, no web framework.

## Tech stack

- **Python 3.11+** (uses stdlib `tomllib`).
- **Core (stdlib only):** `http.server` (receiver), `hmac` + `hashlib` (verify),
  `sqlite3` (capture storage).
- **Runtime deps:** `typer` (CLI), `httpx` (replay), `rich` (pretty-print).
- **Packaging:** hatchling → PyPI / `pipx`. Entry point `hookrunner = hookrunner.cli:app`.

## Layout

```
hookrunner/
├── __init__.py
├── cli.py       # typer app: serve / list / show / replay
├── server.py    # http.server receiver + capture
├── store.py     # sqlite3 persistence
├── config.py    # tomllib loader -> SchemeConfig
├── schemes.py   # verify() + sign() per scheme
└── render.py    # rich pretty-print
```

Docs live in `docs/` — PRD, REQUIREMENTS, SPEC, ROADMAP, TASKS. Read SPEC before
touching schemes/server/store.

## Dev setup

```sh
make install     # venv + compile lockfiles + sync deps + install pre-commit hooks
```

Individual targets: `make venv`, `make compile`, `make sync`, `make hooks`.

## Commands

```sh
make lint        # ruff check .
make fmt         # ruff format .
make test        # pytest
make cov         # pytest with coverage
make compile     # regenerate requirements/*.txt after editing *.in or pyproject deps
```

## Dependency management

- **Runtime deps: two places, keep in sync** — `pyproject.toml`
  `[project.dependencies]` (packaging source of truth) AND `requirements/base.in`
  (pinned dev workflow). A pre-commit hook recompiles `*.txt` when either changes.
- Dev deps: `pyproject.toml` `[project.optional-dependencies].dev` and
  `requirements/dev.in`.
- Never hand-edit `requirements/*.txt` — regenerate with `make compile`.

## Conventions

- **Byte-exact body.** Never decode/re-encode a request body before verifying or
  replaying — signatures are over raw bytes. Store as BLOB.
- **Constant-time compare.** All signature checks use `hmac.compare_digest`.
- **Verify never rejects.** Receiver always returns 200; verification result is
  stored (`verified`, `verify_error`), never used to reject the request.
- **Scheme dispatch by header presence** (`Stripe-Signature`, `X-Hub-Signature-256`,
  configured custom header).
- ruff: line-length 100, rules `E,F,I,UP,B,SIM`. mypy strict.

## Git workflow

- Never commit to `main` — feature branch first (root commit was the one exception).
- Conventional Commits (`feat|fix|refactor|docs|test|chore`), atomic.
- No AI attribution footer.

## Gotchas

- `webhooks.toml` holds secrets → gitignored. Ship `webhooks.example.toml` as the
  reference (not yet created — v1 task).
- Custom scheme `signed_payload` template placeholders: `{body}`, `{timestamp}`,
  `{nonce}`.
- Replay recomputes the signature with a **fresh** timestamp; schemes without a
  timestamp (GitHub) just recompute over the body.

## Roadmap

v1 = capture/verify/inspect/replay (current). v2 = config CLI. v3 = TUI. See
`docs/ROADMAP.md`.
