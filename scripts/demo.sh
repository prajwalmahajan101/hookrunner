#!/usr/bin/env bash
# End-to-end demo: capture test hooks for every scheme, inspect, then replay one
# to a second receiver that re-verifies it. Uses the project venv.
set -euo pipefail
cd "$(dirname "$0")/.."

HR=.venv/bin/hookrunner
PY=.venv/bin/python
TMP="$(mktemp -d)"
CAP="$TMP/capture.db"
TGT="$TMP/target.db"

cat > "$TMP/webhooks.toml" <<'TOML'
[stripe]
secret = "demo"
[github]
secret = "demo"
[optimo]
secret = "demo"
[custom.partnerx]
header = "X-Partner-Signature"
signed_payload = "{timestamp}.{body}"
prefix = "sha256="
timestamp_header = "X-Partner-Timestamp"
secret = "demo"
TOML

echo "== starting receivers (capture:9400, target:9401) =="
"$HR" serve --secret-file "$TMP/webhooks.toml" --port 9400 --db "$CAP" >/dev/null 2>&1 &
CAP_PID=$!
"$HR" serve --secret-file "$TMP/webhooks.toml" --port 9401 --db "$TGT" >/dev/null 2>&1 &
TGT_PID=$!
trap 'kill $CAP_PID $TGT_PID 2>/dev/null || true' EXIT

# Wait for both ports without a bare shell sleep loop.
"$PY" - <<'PY'
import socket, time
for port in (9400, 9401):
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
PY

echo "== sending test hooks =="
"$PY" scripts/send_hooks.py http://127.0.0.1:9400

echo
echo "== hookrunner list (capture) =="
"$HR" list --db "$CAP"

echo
echo "== hookrunner show 1 =="
"$HR" show 1 --db "$CAP"

echo
echo "== replay hook 1 -> target:9401 =="
"$HR" replay 1 --to http://127.0.0.1:9401/webhook --secret-file "$TMP/webhooks.toml" --db "$CAP"

echo
echo "== target receiver saw the replay (verified) =="
"$HR" list --db "$TGT"
