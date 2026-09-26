import pytest

from hookrunner.config import ConfigError, SchemeConfig, load_config

EXAMPLE = "webhooks.example.toml"


def test_loads_example_config():
    schemes = load_config(EXAMPLE)
    assert set(schemes) == {"stripe", "github", "optimo", "partnerx"}
    assert all(isinstance(s, SchemeConfig) for s in schemes.values())


def test_builtins_marked_builtin():
    schemes = load_config(EXAMPLE)
    assert schemes["stripe"].builtin is True
    assert schemes["github"].builtin is True
    assert schemes["optimo"].builtin is True
    assert schemes["partnerx"].builtin is False


def test_custom_scheme_fields():
    partnerx = load_config(EXAMPLE)["partnerx"]
    assert partnerx.header == "X-Partner-Signature"
    assert partnerx.algo == "sha256"
    assert partnerx.signed_payload == "{timestamp}.{body}"
    assert partnerx.encoding == "hex"
    assert partnerx.prefix == "sha256="
    assert partnerx.secret == "your_partnerx_secret"


def _write(tmp_path, text):
    p = tmp_path / "webhooks.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_missing_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config("does_not_exist.toml")


def test_invalid_toml(tmp_path):
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(_write(tmp_path, "this is = = not toml"))


def test_unknown_table(tmp_path):
    with pytest.raises(ConfigError, match="unknown top-level table"):
        load_config(_write(tmp_path, '[paypal]\nsecret = "x"\n'))


def test_builtin_missing_secret(tmp_path):
    with pytest.raises(ConfigError, match="requires a non-empty string 'secret'"):
        load_config(_write(tmp_path, "[stripe]\n"))


def test_custom_name_collides_with_builtin(tmp_path):
    toml = '[custom.stripe]\nheader = "X"\nsecret = "s"\n'
    with pytest.raises(ConfigError, match="collides with a built-in"):
        load_config(_write(tmp_path, toml))


def test_custom_missing_header(tmp_path):
    with pytest.raises(ConfigError, match="requires a non-empty string 'header'"):
        load_config(_write(tmp_path, '[custom.p]\nsecret = "s"\n'))


def test_custom_bad_algo(tmp_path):
    toml = '[custom.p]\nheader = "X"\nsecret = "s"\nalgo = "md5"\n'
    with pytest.raises(ConfigError, match="algo='md5' invalid"):
        load_config(_write(tmp_path, toml))


def test_custom_bad_encoding(tmp_path):
    toml = '[custom.p]\nheader = "X"\nsecret = "s"\nencoding = "base32"\n'
    with pytest.raises(ConfigError, match="encoding='base32' invalid"):
        load_config(_write(tmp_path, toml))


def test_custom_defaults(tmp_path):
    toml = '[custom.p]\nheader = "X-Sig"\nsecret = "s"\n'
    p = load_config(_write(tmp_path, toml))["p"]
    assert p.algo == "sha256"
    assert p.encoding == "hex"
    assert p.signed_payload == "{body}"
    assert p.prefix == ""
    assert p.timestamp_header is None
    assert p.nonce_header is None


def test_custom_timestamp_requires_header(tmp_path):
    toml = '[custom.p]\nheader = "X"\nsecret = "s"\nsigned_payload = "{timestamp}.{body}"\n'
    with pytest.raises(ConfigError, match="no 'timestamp_header'"):
        load_config(_write(tmp_path, toml))


def test_custom_nonce_requires_header(tmp_path):
    toml = '[custom.p]\nheader = "X"\nsecret = "s"\nsigned_payload = "{nonce}.{body}"\n'
    with pytest.raises(ConfigError, match="no 'nonce_header'"):
        load_config(_write(tmp_path, toml))


def test_example_partnerx_has_timestamp_header():
    assert load_config(EXAMPLE)["partnerx"].timestamp_header == "X-Partner-Timestamp"
