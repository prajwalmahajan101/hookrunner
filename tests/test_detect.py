from hookrunner.config import SchemeConfig
from hookrunner.server import detect_scheme

GH = SchemeConfig(name="github", secret="s", builtin=True)
STRIPE = SchemeConfig(name="stripe", secret="s", builtin=True)
CUSTOM = SchemeConfig(name="partnerx", secret="s", header="X-Partner-Signature")


def test_detects_github():
    schemes = {"github": GH}
    assert detect_scheme(schemes, {"X-Hub-Signature-256": "sha256=x"}) is GH


def test_detects_custom_by_header():
    schemes = {"partnerx": CUSTOM}
    assert detect_scheme(schemes, {"X-Partner-Signature": "x"}) is CUSTOM


def test_builtin_precedence_over_custom():
    schemes = {"stripe": STRIPE, "partnerx": CUSTOM}
    headers = {"Stripe-Signature": "t=1,v1=x", "X-Partner-Signature": "y"}
    assert detect_scheme(schemes, headers) is STRIPE


def test_no_match_returns_none():
    assert detect_scheme({"github": GH}, {"Content-Type": "application/json"}) is None


def test_unconfigured_scheme_not_matched():
    # github header present but github not configured
    assert detect_scheme({"stripe": STRIPE}, {"X-Hub-Signature-256": "sha256=x"}) is None
