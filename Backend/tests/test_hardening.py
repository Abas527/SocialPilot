from dataclasses import replace

from fastapi.testclient import TestClient

from api import main
from core import ratelimit

CASE_STUDY = {
    "title": "T", "summary": "s", "problem": "p", "architecture": "a",
    "implementation": "i", "challenges": "c", "results": "r",
    "limitations": "l", "future_work": "f",
}


def test_export_endpoints_require_authentication():
    client = TestClient(main.app)
    assert client.post("/export/markdown", json=CASE_STUDY).status_code == 401
    assert client.post("/export/pdf", json=CASE_STUDY).status_code == 401


def test_login_is_rate_limited_per_ip(monkeypatch):
    # The limit dependency was built at import time, so patch the shared check.
    monkeypatch.setattr(ratelimit, "settings", replace(ratelimit.settings, rate_limit_enabled=True))
    client = TestClient(main.app)
    statuses = [
        client.post("/auth/login", json={"email": "x@example.test", "password": "nope"}).status_code
        for _ in range(main.settings.auth_rate_limit_per_min + 2)
    ]
    assert statuses[0] == 401
    assert statuses[-1] == 429
    blocked = client.post("/auth/login", json={"email": "x@example.test", "password": "nope"})
    assert blocked.headers["Retry-After"].isdigit()


def test_rate_limiter_window_and_disable(monkeypatch):
    for _ in range(3):
        ratelimit.check("k", 3, 60)
    try:
        ratelimit.check("k", 3, 60)
        raise AssertionError("expected 429")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
    monkeypatch.setattr(ratelimit, "settings", replace(ratelimit.settings, rate_limit_enabled=False))
    ratelimit.check("k", 3, 60)  # disabled -> never raises
