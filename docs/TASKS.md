# hookrunner — v1 Task Breakdown

Ordered, bite-sized tasks to build v1. Each maps to requirements (FR/NFR) and is
a candidate atomic commit. Check off as completed.

## 0. Project scaffold

- [ ] `pyproject.toml` — project metadata, deps (`typer`, `httpx`, `rich`),
      `hookrunner` console-script entry point, Python 3.11+ pin. (NFR-1, NFR-3)
- [ ] Package skeleton: `hookrunner/{__init__,cli,server,store,config,schemes,render}.py`.
- [ ] Dev tooling: `ruff`, `pytest`, `pytest-cov` in a `[dev]` extra.

## 1. Config loader (`config.py`)

- [ ] `SchemeConfig` dataclass (header, algo, signed_payload, encoding, prefix, secret).
- [ ] `load_config(path) -> dict[str, SchemeConfig]` via `tomllib`. (FR-17)
- [ ] Built-in defaults for stripe/github/optimo (only `secret` required from TOML).
- [ ] `webhooks.example.toml` covering all four schemes. (FR-18)
- [ ] Test: load example config, assert parsed schemes.

## 2. Signature schemes (`schemes.py`)

- [ ] `VerifyError` exception.
- [ ] Stripe `verify` + `sign`. (FR-7)
- [ ] GitHub `verify` + `sign`. (FR-8)
- [ ] Generic HMAC+nonce `verify` + `sign`. (FR-9)
- [ ] Custom (template-driven) `verify` + `sign`. (FR-10)
- [ ] All comparisons via `hmac.compare_digest`. (FR-11)
- [ ] Tests: real captured Stripe + GitHub test events verify pass/fail. (NFR-5, 80%+)

## 3. Storage (`store.py`)

- [ ] Create `hooks` table on first use (schema per SPEC).
- [ ] `insert_hook(...) -> id`. (FR-2)
- [ ] `list_hooks()`, `get_hook(id)`.
- [ ] Body stored as BLOB, byte-exact. (NFR-6)
- [ ] Test: insert → get round-trips body bytes exactly.

## 4. Receiver (`server.py`)

- [ ] `http.server` handler: read exact `Content-Length` body. (FR-1)
- [ ] Scheme detection by header presence. (FR-3)
- [ ] Verify + record result; never crash on failure. (FR-4, FR-6)
- [ ] Always respond 200 with `{id, verified}`. (FR-5)
- [ ] Insert into store. (FR-2)
- [ ] Test: POST signed + unsigned bodies, assert stored rows + verify flags.

## 5. CLI (`cli.py`)

- [ ] `typer` app skeleton, `--db` global option.
- [ ] `serve --port --secret-file [--db]`. (FR-1)
- [ ] `list`. (FR-12)
- [ ] `show <id>`. (FR-13)
- [ ] `replay <id> --to <url>`. (FR-14, FR-15, FR-16)

## 6. Rendering (`render.py`)

- [ ] `rich` table for `list`.
- [ ] `show` pretty-print: headers + JSON-highlighted body + verify status. (FR-13)

## 7. Replay (`cli.py` + `schemes.sign`)

- [ ] Load hook, resolve scheme, recompute signature with fresh timestamp. (FR-16)
- [ ] Swap old signature header(s) for new; POST via `httpx`. (FR-14, FR-15)
- [ ] Print target response. 
- [ ] Test: replay a captured hook to a local test receiver; assert it verifies.

## 8. Packaging & docs

- [ ] Verify `pipx install .` works locally. (NFR-4)
- [ ] README usage + 60-second screencast. (DoD)
- [ ] CI: lint + test + coverage gate (80%+ on schemes). (NFR-5)
- [ ] Publish to PyPI.

## Suggested build order

Config → schemes → store → server → CLI/render → replay → packaging. Schemes
first (with tests) de-risks the hardest, highest-value part before wiring I/O.
