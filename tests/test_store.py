from hookrunner.store import Store

RAW_BODY = b'{"a": 1}\x00\xff\x80 binary-\xe2\x9c\x93'


def _db(tmp_path):
    return Store(tmp_path / "hooks.db")


def _insert(store, **overrides):
    fields = dict(
        received_at="2026-01-01T00:00:00Z",
        remote_addr="127.0.0.1",
        method="POST",
        path="/webhook",
        headers={"Content-Type": "application/json"},
        body=RAW_BODY,
        scheme="github",
        verified=True,
        verify_error=None,
    )
    fields.update(overrides)
    return store.insert(**fields)


def test_insert_get_roundtrips_body_bytes_exactly(tmp_path):
    store = _db(tmp_path)
    hook_id = _insert(store)
    got = store.get(hook_id)
    assert got is not None
    assert got.body == RAW_BODY
    assert isinstance(got.body, bytes)
    store.close()
