# hookrunner — Requirements

Requirements are labelled `FR` (functional) and `NFR` (non-functional). Each has a
priority: **MUST** (v1), **SHOULD** (v1 if time allows), **COULD** (stretch).

## Functional requirements

### Receiver

- **FR-1 (MUST)** — `hookrunner serve --port <port> --secret-file <path>` starts a
  local HTTP server that accepts arbitrary POST requests on any path.
- **FR-2 (MUST)** — The receiver persists every received request to a SQLite file:
  received timestamp, remote address, method, path, headers, byte-exact body,
  detected scheme, verification result, and verification error (if any).
- **FR-3 (MUST)** — The receiver detects the signature scheme by header presence
  (`Stripe-Signature` → stripe, `X-Hub-Signature-256` → github, configured custom
  header → custom).
- **FR-4 (MUST)** — The receiver verifies the signature using the per-scheme secret
  loaded from the secret file, and records whether it passed.
- **FR-5 (MUST)** — The receiver always responds `200 OK` regardless of the
  verification result. The result is stored, never used to reject the request.
- **FR-6 (MUST)** — A verification failure never crashes the receiver; the reason
  is recorded in `verify_error`.

### Signature schemes

- **FR-7 (MUST)** — Verify Stripe signatures (`Stripe-Signature`, `t=` timestamp +
  `v1=` HMAC-SHA256 over `timestamp.body`).
- **FR-8 (MUST)** — Verify GitHub signatures (`X-Hub-Signature-256`, `sha256=` HMAC
  over the raw body).
- **FR-9 (MUST)** — Verify a generic HMAC+nonce scheme (Optimo-style).
- **FR-10 (MUST)** — Verify a custom scheme defined in TOML with fields: `header`,
  `algo` (`sha256`/`sha1`), `signed_payload` template, `encoding` (`hex`/`base64`),
  and `prefix`.
- **FR-11 (MUST)** — All signature comparisons use a constant-time comparison
  (`hmac.compare_digest`).

### Inspection

- **FR-12 (MUST)** — `hookrunner list` lists captured hooks (id, time, scheme,
  verified status).
- **FR-13 (MUST)** — `hookrunner show <id>` pretty-prints one hook: headers, body
  (JSON syntax-highlighted when applicable), and verification status.

### Replay

- **FR-14 (MUST)** — `hookrunner replay <id> --to <url>` re-sends a captured hook
  to the target URL.
- **FR-15 (MUST)** — Replay signs the outgoing request with the same per-scheme
  secret from the secret file.
- **FR-16 (MUST)** — Replay stamps a fresh timestamp and recomputes the signature
  per scheme, so a receiver's freshness/signature checks pass. Schemes without a
  timestamp recompute over the body only.

### Configuration

- **FR-17 (MUST)** — Secrets and custom-scheme definitions load from a TOML file
  (`webhooks.toml`), one secret per scheme. v1 is hand-edited only — no CLI
  config management.
- **FR-18 (MUST)** — Ship a `webhooks.example.toml` documenting every scheme's
  config shape as a copy-paste starting point.

## Non-functional requirements

- **NFR-1 (MUST)** — Python 3.11+ (uses stdlib `tomllib`).
- **NFR-2 (MUST)** — No web framework. Receiver uses stdlib `http.server`,
  `hmac`, `hashlib`, `sqlite3`.
- **NFR-3 (MUST)** — Runtime dependencies limited to `typer`, `httpx`, `rich`.
- **NFR-4 (MUST)** — `pipx install hookrunner` works clean on Linux, macOS, and
  Windows.
- **NFR-5 (MUST)** — 80%+ test coverage on signature-verification code paths.
- **NFR-6 (SHOULD)** — Body stored byte-exact so signature verification is never
  broken by re-encoding.
- **NFR-7 (COULD)** — TUI mode (`hookrunner tui`) using Textual.
- **NFR-8 (COULD)** — HAR-style export of captured hooks.
- **NFR-9 (COULD)** — `hookrunner test <url>` synthetic webhook generation for load
  testing.

## Deferred to later versions

- **v2** — CLI config management: `hookrunner config add <scheme> --secret ...`,
  `config list`, `config remove <scheme>` (read + write `webhooks.toml`, secret
  validation, masked display).
- **v3 / stretch** — Full TUI (`hookrunner tui`), if config CLI proves insufficient.
