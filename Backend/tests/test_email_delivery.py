from dataclasses import replace

import httpx
import pytest

from config import settings as default_settings
from core import email_delivery


def _brevo_settings():
    return replace(
        default_settings,
        email_provider="brevo",
        brevo_api_key="test-brevo-key",
        smtp_from="SocialPilot <verified@example.test>",
        smtp_timeout_s=7,
        public_api_url="https://socialpilot.example",
    )


def test_brevo_configuration_requires_api_key_and_safe_sender(monkeypatch):
    configured = _brevo_settings()
    monkeypatch.setattr(email_delivery, "settings", configured)
    assert email_delivery.is_configured()

    monkeypatch.setattr(
        email_delivery,
        "settings",
        replace(configured, brevo_api_key=""),
    )
    assert not email_delivery.is_configured()

    monkeypatch.setattr(
        email_delivery,
        "settings",
        replace(configured, smtp_from="unverified sender"),
    )
    assert not email_delivery.is_configured()


def test_brevo_sends_transactional_verification_email(monkeypatch):
    configured = _brevo_settings()
    monkeypatch.setattr(email_delivery, "settings", configured)
    requests = []

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return httpx.Response(
            201,
            request=httpx.Request("POST", url),
            json={"messageId": "<message@example.test>"},
        )

    monkeypatch.setattr(email_delivery.httpx, "post", fake_post)
    email_delivery.send_verification_email(
        "user@example.test",
        "Anil <Builder>",
        "verification-token",
    )

    url, request = requests[0]
    assert url == email_delivery.BREVO_TRANSACTIONAL_EMAIL_URL
    assert request["headers"]["api-key"] == "test-brevo-key"
    assert request["timeout"] == 7
    assert request["json"]["sender"] == {
        "name": "SocialPilot",
        "email": "verified@example.test",
    }
    assert request["json"]["to"] == [
        {"email": "user@example.test", "name": "Anil <Builder>"}
    ]
    assert "api-key" not in request["json"]
    assert "https://socialpilot.example/auth/verify-email#token=verification-token" in (
        request["json"]["textContent"]
    )
    assert "&lt;Builder&gt;" in request["json"]["htmlContent"]


def test_brevo_http_failure_has_explicit_delivery_error(monkeypatch):
    configured = _brevo_settings()
    monkeypatch.setattr(email_delivery, "settings", configured)

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(email_delivery.httpx, "post", fake_post)
    with pytest.raises(email_delivery.EmailDeliveryError, match="HTTP 401"):
        email_delivery.send_verification_email(
            "user@example.test", "Builder", "verification-token"
        )
