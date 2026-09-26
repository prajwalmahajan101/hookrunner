import threading

import httpx
import pytest

from hookrunner.config import SchemeConfig
from hookrunner.schemes import sign
from hookrunner.server import HookServer
from hookrunner.store import Store

BODY = b'{"event":"x"}\x00\xff binary'
CFG = SchemeConfig(name="github", secret="s3cr3t", builtin=True)


@pytest.fixture
def server(tmp_path):
    store = Store(tmp_path / "h.db")
    schemes = {"github": CFG}
    srv = HookServer(("127.0.0.1", 0), schemes, store)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, store
    finally:
        srv.shutdown()
        srv.server_close()
        store.close()


def _post(port, body, headers):
    return httpx.post(f"http://127.0.0.1:{port}/webhook", content=body, headers=headers)


def test_valid_signature_captured_verified(server):
    port, store = server
    resp = _post(port, BODY, sign(CFG, BODY, 0))
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    hook = store.get(body["id"])
    assert hook.verified is True
    assert hook.scheme == "github"
    assert hook.body == BODY  # byte-exact


def test_bad_signature_still_200_and_recorded(server):
    port, store = server
    headers = sign(CFG, BODY, 0)
    resp = _post(port, BODY + b"tamper", headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is False
    hook = store.get(body["id"])
    assert hook.verified is False
    assert hook.verify_error


def test_no_scheme_header_captured_unverified(server):
    port, store = server
    resp = _post(port, BODY, {"Content-Type": "application/json"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is None
    hook = store.get(body["id"])
    assert hook.scheme is None
    assert hook.verified is None
    assert hook.body == BODY
