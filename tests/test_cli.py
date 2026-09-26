import threading

from typer.testing import CliRunner

from hookrunner.cli import app, build_replay_headers
from hookrunner.config import SchemeConfig
from hookrunner.schemes import sign, verify
from hookrunner.server import HookServer
from hookrunner.store import Store

runner = CliRunner()
CFG = SchemeConfig(name="github", secret="s3cr3t", builtin=True)
BODY = b'{"event":"x"}'


def _capture(db_path):
    """Insert one signed github hook and return its id."""
    store = Store(db_path)
    headers = dict(sign(CFG, BODY, 0))
    hook_id = store.insert(
        received_at="2026-01-01T00:00:00Z",
        remote_addr="127.0.0.1",
        method="POST",
        path="/webhook",
        headers=headers,
        body=BODY,
        scheme="github",
        verified=True,
        verify_error=None,
    )
    store.close()
    return hook_id


def test_list_and_show(tmp_path):
    db = tmp_path / "h.db"
    hook_id = _capture(db)
    res = runner.invoke(app, ["list", "--db", str(db)])
    assert res.exit_code == 0
    assert str(hook_id) in res.stdout

    res = runner.invoke(app, ["show", str(hook_id), "--db", str(db)])
    assert res.exit_code == 0
    assert "github" in res.stdout


def test_show_missing_exits_1(tmp_path):
    db = tmp_path / "h.db"
    Store(db).close()
    res = runner.invoke(app, ["show", "999", "--db", str(db)])
    assert res.exit_code == 1


def test_build_replay_headers_produces_valid_signature():
    original = {
        "X-Hub-Signature-256": "sha256=stale",
        "Host": "old",
        "Content-Length": "5",
        "Content-Type": "application/json",
    }
    headers = build_replay_headers(CFG, original, BODY, timestamp=123)
    assert "Host" not in headers
    assert "Content-Length" not in headers
    assert headers["Content-Type"] == "application/json"
    verify(CFG, headers, BODY)  # fresh signature must verify


def test_replay_to_live_receiver(tmp_path):
    db = tmp_path / "capture.db"
    hook_id = _capture(db)
    cfg_file = tmp_path / "webhooks.toml"
    cfg_file.write_text('[github]\nsecret = "s3cr3t"\n', encoding="utf-8")

    target_store = Store(tmp_path / "target.db")
    srv = HookServer(("127.0.0.1", 0), {"github": CFG}, target_store)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        res = runner.invoke(
            app,
            [
                "replay",
                str(hook_id),
                "--to",
                f"http://127.0.0.1:{port}/webhook",
                "--secret-file",
                str(cfg_file),
                "--db",
                str(db),
            ],
        )
        assert res.exit_code == 0, res.stdout
        assert "200" in res.stdout
        received = target_store.list_hooks()
        assert len(received) == 1
        assert received[0].verified is True
        assert received[0].body == BODY
    finally:
        srv.shutdown()
        srv.server_close()
        target_store.close()
