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


def test_get_missing_returns_none(tmp_path):
    with _db(tmp_path) as store:
        assert store.get(999) is None


def test_headers_and_metadata_roundtrip(tmp_path):
    with _db(tmp_path) as store:
        hook_id = _insert(
            store, headers={"X-A": "1", "X-B": "2"}, path="/p", remote_addr="10.0.0.5"
        )
        got = store.get(hook_id)
        assert got is not None
        assert got.headers == {"X-A": "1", "X-B": "2"}
        assert got.path == "/p"
        assert got.remote_addr == "10.0.0.5"


def test_list_orders_newest_first(tmp_path):
    with _db(tmp_path) as store:
        first = _insert(store, path="/first")
        second = _insert(store, path="/second")
        hooks = store.list_hooks()
        assert [h.id for h in hooks] == [second, first]


def test_verified_tri_state(tmp_path):
    with _db(tmp_path) as store:
        passed = _insert(store, verified=True, verify_error=None)
        failed = _insert(store, verified=False, verify_error="signature mismatch")
        none = _insert(store, scheme=None, verified=None, verify_error=None)
        assert store.get(passed).verified is True
        assert store.get(failed).verified is False
        assert store.get(failed).verify_error == "signature mismatch"
        assert store.get(none).verified is None
