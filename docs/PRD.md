# hookrunner — Product Requirements Document

## Summary

hookrunner is a local, single-binary developer tool for capturing, inspecting,
and replaying HMAC-signed webhooks. It runs a local HTTP server that receives
webhooks from producers (Stripe, GitHub, partner integrations), verifies their
signatures, persists every request to a SQLite file, and lets the developer
inspect and replay them against a local service with the signature still
verifying.

## Problem

Testing webhook integrations locally is painful. Tunnelling tools (ngrok) forward
traffic but do not help a developer *capture, inspect, and replay* signed
webhooks. When a webhook fails locally, the developer cannot easily see the exact
payload, confirm whether the signature verified, or re-send the same event
without triggering a new one from the producer. Signed webhooks make this worse:
replaying a captured request normally breaks the signature because the timestamp
or nonce is stale.

## Target user

Backend developers integrating third-party or partner webhooks who work against a
local service and need a fast capture → inspect → replay loop without a public
web service.

## Goals

- Capture every received webhook with full fidelity (headers + byte-exact body).
- Verify signatures for Stripe, GitHub, generic HMAC+nonce, and a user-defined
  custom scheme.
- Let the developer inspect any captured webhook, including its verification
  status.
- Replay any captured webhook to a local URL with a freshly recomputed, valid
  signature.
- Ship as a zero-heavy-dependency, `pipx`-installable CLI.

## Non-goals

- Tunnelling / public exposure (use ngrok or similar).
- Generating webhooks from scratch as a producer.
- A TUI (stretch goal, not v1).

## Success metrics

- All four signature schemes verify correctly against real captured Stripe and
  GitHub test events.
- `pipx install hookrunner` works clean on Linux, macOS, and Windows.
- 80%+ test coverage on signature-verification code paths.
- A developer can complete a capture → inspect → replay loop in under 60 seconds.

## Key decisions

| Area | Decision |
|---|---|
| Language | Python 3.11+ |
| CLI framework | `typer` |
| Scheme dispatch | By signature-header presence |
| Custom scheme config | Full TOML template (header, algo, signed_payload, encoding, prefix) |
| Verify-fail HTTP response | Always 200, verification result stored |
| Replay signing secret | Same secret from `webhooks.toml` |
| Replay timestamp | Fresh timestamp + per-scheme recompute |
| Storage | SQLite, body stored byte-exact as BLOB |
