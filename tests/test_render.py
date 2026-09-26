from io import StringIO

from rich.console import Console

from hookrunner.render import render_list, render_show
from hookrunner.store import Hook


def _console():
    return Console(file=StringIO(), width=200, force_terminal=False)


def _hook(**kw):
    fields = dict(
        id=1,
        received_at="2026-01-01T00:00:00Z",
        remote_addr="127.0.0.1",
        method="POST",
        path="/webhook",
        headers={"Content-Type": "application/json"},
        body=b'{"a": 1}',
        scheme="github",
        verified=True,
        verify_error=None,
    )
    fields.update(kw)
    return Hook(**fields)


def test_render_list_includes_rows():
    c = _console()
    render_list([_hook(id=7, scheme="stripe")], c)
    out = c.file.getvalue()
    assert "7" in out
    assert "stripe" in out
    assert "verified" in out


def test_render_show_json_body():
    c = _console()
    render_show(_hook(), c)
    out = c.file.getvalue()
    assert "#1" in out
    assert "Content-Type" in out
    assert "github" in out


def test_render_show_failed_shows_error():
    c = _console()
    render_show(_hook(verified=False, verify_error="signature mismatch"), c)
    out = c.file.getvalue()
    assert "FAILED" in out
    assert "signature mismatch" in out


def test_render_show_non_json_body():
    c = _console()
    render_show(_hook(body=b"\xff\xfe not json"), c)
    out = c.file.getvalue()
    assert "#1" in out
