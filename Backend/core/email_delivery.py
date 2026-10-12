"""SMTP delivery for account verification messages."""
from email.utils import parseaddr
from html import escape
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit

import httpx

from config import settings

BREVO_TRANSACTIONAL_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"


class EmailDeliveryError(RuntimeError):
    """Raised when verification email cannot be safely delivered."""


def is_configured() -> bool:
    public_url = urlsplit(settings.public_api_url)
    public_url_is_safe = (
        public_url.scheme == "https" and bool(public_url.netloc)
    ) or (
        public_url.scheme == "http"
        and public_url.hostname in {"localhost", "127.0.0.1", "::1"}
    )
    sender_email = parseaddr(settings.smtp_from)[1]
    if not sender_email or "@" not in sender_email or not public_url_is_safe:
        return False
    if settings.email_provider == "brevo":
        return bool(settings.brevo_api_key.strip() and settings.smtp_timeout_s > 0)
    if settings.email_provider == "smtp":
        return bool(
            settings.smtp_host.strip()
            and 0 < settings.smtp_port <= 65535
            and settings.smtp_timeout_s > 0
            and (bool(settings.smtp_username.strip()) == bool(settings.smtp_password))
            and (settings.smtp_use_ssl or settings.smtp_starttls)
            and not (settings.smtp_use_ssl and settings.smtp_starttls)
        )
    return False


def send_verification_email(email: str, display_name: str, token: str) -> None:
    if not is_configured():
        raise EmailDeliveryError("Email delivery is not configured.")
    if settings.email_verification_ttl_hours <= 0:
        raise EmailDeliveryError(
            "EMAIL_VERIFICATION_TTL_HOURS must be greater than zero."
        )

    verification_url = (
        f"{settings.public_api_url.rstrip('/')}/auth/verify-email"
        f"#token={token}"
    )
    if settings.email_provider == "brevo":
        _send_brevo_verification_email(email, display_name, verification_url)
        return

    message = EmailMessage()
    message["Subject"] = "Verify your SocialPilot account"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        f"""Hello {display_name},

Verify your SocialPilot account by opening this link:
{verification_url}

For security, the link expires in {settings.email_verification_ttl_hours} hours.
If you did not create this account, you can ignore this email.
"""
    )

    context = ssl.create_default_context()
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_s,
                context=context,
            ) as smtp:
                _authenticate_and_send(smtp, message)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_s,
            ) as smtp:
                smtp.ehlo()
                if settings.smtp_starttls:
                    smtp.starttls(context=context)
                    smtp.ehlo()
                _authenticate_and_send(smtp, message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Verification email could not be delivered.") from exc


def _send_brevo_verification_email(
    email: str, display_name: str, verification_url: str
) -> None:
    sender_name, sender_email = parseaddr(settings.smtp_from)
    safe_name = escape(display_name)
    safe_url = escape(verification_url, quote=True)
    payload = {
        "sender": {
            "name": sender_name or "SocialPilot",
            "email": sender_email,
        },
        "to": [{"email": email, "name": display_name}],
        "subject": "Verify your SocialPilot account",
        "textContent": (
            f"Hello {display_name},\n\n"
            "Verify your SocialPilot account by opening this link:\n"
            f"{verification_url}\n\n"
            f"For security, the link expires in "
            f"{settings.email_verification_ttl_hours} hours.\n"
            "If you did not create this account, you can ignore this email."
        ),
        "htmlContent": (
            f"<p>Hello {safe_name},</p>"
            "<p>Verify your SocialPilot account by selecting the link below:</p>"
            f'<p><a href="{safe_url}">Verify your email address</a></p>'
            "<p>For security, the link expires in "
            f"{settings.email_verification_ttl_hours} hours.</p>"
            "<p>If you did not create this account, you can ignore this email.</p>"
        ),
    }
    try:
        response = httpx.post(
            BREVO_TRANSACTIONAL_EMAIL_URL,
            headers={
                "api-key": settings.brevo_api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            json=payload,
            timeout=settings.smtp_timeout_s,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise EmailDeliveryError(
            f"Brevo rejected the verification email (HTTP "
            f"{exc.response.status_code})."
        ) from exc
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(
            "Could not connect to Brevo to send the verification email."
        ) from exc


def _authenticate_and_send(smtp: smtplib.SMTP, message: EmailMessage) -> None:
    if settings.smtp_username:
        smtp.login(settings.smtp_username, settings.smtp_password)
    smtp.send_message(message)
