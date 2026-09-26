import base64
import hashlib
import hmac

import pytest

from hookrunner.config import SchemeConfig
from hookrunner.schemes import (
    OPTIMO_NONCE_HEADER,
    OPTIMO_SIG_HEADER,
    OPTIMO_TIMESTAMP_HEADER,
    VerifyError,
    sign,
    verify,
)

BODY = b'{"event":"test","amount":100}'


def _cfg(name, **kw):
    builtin = name in {"stripe", "github", "optimo"}
    return SchemeConfig(name=name, secret="s3cr3t", builtin=builtin, **kw)


# --- github ---------------------------------------------------------------


def test_github_known_vector():
    # Official GitHub docs example.
    secret = "It's a Secret to Everybody"
    body = b"Hello, World!"
    expected = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
    cfg = SchemeConfig(name="github", secret=secret, builtin=True)
    verify(cfg, {"X-Hub-Signature-256": expected}, body)


def test_github_roundtrip():
    cfg = _cfg("github")
    headers = sign(cfg, BODY, timestamp=0)
    verify(cfg, headers, BODY)


def test_github_tamper_fails():
    cfg = _cfg("github")
    headers = sign(cfg, BODY, timestamp=0)
    with pytest.raises(VerifyError, match="mismatch"):
        verify(cfg, headers, BODY + b"x")


def test_github_missing_header():
    with pytest.raises(VerifyError, match="missing header"):
        verify(_cfg("github"), {}, BODY)


# --- stripe ---------------------------------------------------------------


def test_stripe_roundtrip():
    cfg = _cfg("stripe")
    headers = sign(cfg, BODY, timestamp=1700000000)
    assert headers["Stripe-Signature"].startswith("t=1700000000,v1=")
    verify(cfg, headers, BODY)


def test_stripe_manual_vector():
    cfg = _cfg("stripe")
    ts = 1700000000
    sig = hmac.new(cfg.secret.encode(), f"{ts}.".encode() + BODY, hashlib.sha256).hexdigest()
    verify(cfg, {"Stripe-Signature": f"t={ts},v1={sig}"}, BODY)


def test_stripe_multiple_v1_one_matches():
    cfg = _cfg("stripe")
    ts = 1700000000
    good = hmac.new(cfg.secret.encode(), f"{ts}.".encode() + BODY, hashlib.sha256).hexdigest()
    header = f"t={ts},v1=deadbeef,v1={good}"
    verify(cfg, {"Stripe-Signature": header}, BODY)


def test_stripe_tamper_fails():
    cfg = _cfg("stripe")
    headers = sign(cfg, BODY, timestamp=1700000000)
    with pytest.raises(VerifyError, match="mismatch"):
        verify(cfg, headers, BODY + b"x")


def test_stripe_malformed_header():
    with pytest.raises(VerifyError, match="malformed"):
        verify(_cfg("stripe"), {"Stripe-Signature": "garbage"}, BODY)


# --- optimo ---------------------------------------------------------------


def test_optimo_roundtrip():
    cfg = _cfg("optimo")
    headers = sign(cfg, BODY, timestamp=1700000000)
    assert set(headers) == {OPTIMO_SIG_HEADER, OPTIMO_TIMESTAMP_HEADER, OPTIMO_NONCE_HEADER}
    verify(cfg, headers, BODY)


def test_optimo_tamper_fails():
    cfg = _cfg("optimo")
    headers = sign(cfg, BODY, timestamp=1700000000)
    headers[OPTIMO_NONCE_HEADER] = "tampered"
    with pytest.raises(VerifyError, match="mismatch"):
        verify(cfg, headers, BODY)


def test_optimo_missing_timestamp_header():
    cfg = _cfg("optimo")
    headers = sign(cfg, BODY, timestamp=1700000000)
    del headers[OPTIMO_TIMESTAMP_HEADER]
    with pytest.raises(VerifyError, match="missing header"):
        verify(cfg, headers, BODY)


# --- custom ---------------------------------------------------------------


def _partnerx():
    return SchemeConfig(
        name="partnerx",
        secret="s3cr3t",
        header="X-Partner-Signature",
        algo="sha256",
        signed_payload="{timestamp}.{body}",
        encoding="hex",
        prefix="sha256=",
        timestamp_header="X-Partner-Timestamp",
    )


def test_custom_timestamp_roundtrip():
    cfg = _partnerx()
    headers = sign(cfg, BODY, timestamp=1700000000)
    assert headers["X-Partner-Signature"].startswith("sha256=")
    assert headers["X-Partner-Timestamp"] == "1700000000"
    verify(cfg, headers, BODY)


def test_custom_tamper_fails():
    cfg = _partnerx()
    headers = sign(cfg, BODY, timestamp=1700000000)
    with pytest.raises(VerifyError, match="mismatch"):
        verify(cfg, headers, BODY + b"!")


def test_custom_body_only_base64_sha1():
    cfg = SchemeConfig(
        name="c",
        secret="s3cr3t",
        header="X-Sig",
        algo="sha1",
        signed_payload="{body}",
        encoding="base64",
    )
    mac = hmac.new(cfg.secret.encode(), BODY, hashlib.sha1).digest()
    expected = base64.b64encode(mac).decode()
    verify(cfg, {"X-Sig": expected}, BODY)
    assert sign(cfg, BODY, 0) == {"X-Sig": expected}


def test_custom_nonce_roundtrip():
    cfg = SchemeConfig(
        name="c",
        secret="s3cr3t",
        header="X-Sig",
        signed_payload="{nonce}.{body}",
        nonce_header="X-Nonce",
    )
    headers = sign(cfg, BODY, timestamp=0)
    assert "X-Nonce" in headers
    verify(cfg, headers, BODY)


def test_custom_missing_header():
    with pytest.raises(VerifyError, match="missing header"):
        verify(_partnerx(), {}, BODY)


def test_header_lookup_case_insensitive():
    cfg = _cfg("github")
    headers = sign(cfg, BODY, timestamp=0)
    value = headers.pop("X-Hub-Signature-256")
    verify(cfg, {"x-hub-signature-256": value}, BODY)
