# hookrunner — Technical Specification

This document specifies the v1 design: modules, data model, config format, the
four signature schemes, and the request/replay flows.

## Module layout

```
hookrunner/
├── __init__.py
├── cli.py          # typer app: serve / list / show / replay
├── server.py       # http.server receiver + capture
├── store.py        # sqlite3 persistence
├── config.py       # tomllib loader -> SchemeConfig objects
├── schemes.py      # verify() + sign() per scheme
└── render.py       # rich pretty-print for show/list
```

## Data model (SQLite)

One table, `hooks`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | autoincrement rowid |
| `received_at` | TEXT | ISO-8601 UTC |
| `remote_addr` | TEXT | caller IP |
| `method` | TEXT | always `POST` in v1 |
| `path` | TEXT | request path |
| `headers` | TEXT | JSON object of request headers |
| `body` | BLOB | byte-exact request body |
| `scheme` | TEXT | detected scheme, or NULL if none matched |
| `verified` | INTEGER | 1 = passed, 0 = failed, NULL = no scheme |
| `verify_error` | TEXT | failure reason, NULL when verified |

The DB file path defaults to `./hookrunner.db`, overridable with `--db`.

## Config format (`webhooks.toml`)

```toml
[stripe]
secret = "whsec_..."

[github]
secret = "ghsecret..."

[optimo]              # generic HMAC+nonce
secret = "..."

[custom.partnerx]     # custom scheme, table name = scheme id
header = "X-Partner-Signature"
algo = "sha256"                       # sha256 | sha1
signed_payload = "{timestamp}.{body}" # template; placeholders {timestamp}, {body}, {nonce}
encoding = "hex"                      # hex | base64
prefix = "sha256="                   # stripped/prepended before compare
```

Loader (`config.py`) parses this into `SchemeConfig` objects keyed by scheme id.
Built-in schemes (stripe, github, optimo) need only `secret`; their header,
algo, payload template, encoding, and prefix are hard-coded in `schemes.py`.

## Signature schemes (`schemes.py`)

Each scheme implements two functions:

```python
def verify(cfg: SchemeConfig, headers: dict, body: bytes) -> None:
    """Raise VerifyError with a reason on failure; return on success."""


def sign(cfg: SchemeConfig, body: bytes, timestamp: int) -> dict:
    """Return the header(s) to set on a replayed request."""
```

All HMAC comparisons use `hmac.compare_digest`.

### Stripe

- Header: `Stripe-Signature`, format `t=<unix>,v1=<hex>` (may carry multiple `v1`).
- Signed payload: `f"{t}.{body}"` (body as raw bytes).
- Algo: HMAC-SHA256, hex.
- Verify: recompute `v1` over `t.body`; compare against any supplied `v1`.
- Sign (replay): fresh `t = now`, recompute `v1`, emit `t=<now>,v1=<hex>`.

### GitHub

- Header: `X-Hub-Signature-256`, format `sha256=<hex>`.
- Signed payload: raw body only (no timestamp).
- Algo: HMAC-SHA256, hex.
- Verify: recompute over body; compare.
- Sign (replay): recompute over body; timestamp irrelevant.

### Generic HMAC+nonce (Optimo-style)

- Header(s): signature header + nonce header + timestamp header (names fixed in
  `schemes.py`; documented in `webhooks.example.toml`).
- Signed payload: `f"{timestamp}.{nonce}.{body}"`.
- Algo: HMAC-SHA256, hex.
- Verify: recompute; compare; optionally reject stale timestamp (out of scope for
  v1 rejection — we only record the result).
- Sign (replay): fresh timestamp, fresh nonce, recompute.

### Custom (TOML-defined)

- Driven entirely by `SchemeConfig`: `header`, `algo`, `signed_payload` template,
  `encoding`, `prefix`.
- `signed_payload` placeholders: `{body}`, `{timestamp}`, `{nonce}`.
- Verify: render template, HMAC with `algo`, encode with `encoding`, prepend
  `prefix`, compare against header value.
- Sign (replay): same, with fresh `{timestamp}`/`{nonce}` when present in template.

## Request flow (serve)

1. `http.server` handler receives POST; read `Content-Length` bytes exactly.
2. Detect scheme by header presence. First matching known header wins; if none,
   `scheme = NULL`.
3. If a scheme matched and its secret is configured, call `verify()`. Record
   `verified` + `verify_error`.
4. Insert row into `hooks`.
5. Respond `200 OK` with a short JSON body (`{"id": <id>, "verified": <bool|null>}`).

## Replay flow

1. Load hook row by id.
2. Resolve scheme (from stored `scheme`); load its `SchemeConfig`.
3. Call `sign()` with the stored body + fresh timestamp → new signature headers.
4. Rebuild outgoing headers: original headers minus the old signature header(s),
   plus the freshly signed one(s).
5. POST body + headers to `--to <url>` via `httpx`.
6. Print target response status + body via `rich`.

## Error handling

- Malformed signature header → `VerifyError`, recorded, still 200.
- Unknown scheme on replay → hard CLI error (can't recompute).
- Missing secret for a matched scheme → record `verify_error="no secret configured"`.
- Byte-exact body is mandatory; never decode/re-encode before verify or replay.

## Out of scope (v1)

Tunnelling, config-editing CLI (v2), TUI (v3), HAR export, synthetic load test.
