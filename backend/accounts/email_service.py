import logging
import smtplib
from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import BadHeaderError
from django.core.validators import validate_email
from django.utils.html import escape

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Verification email could not be delivered."""


def send_verification_email(recipient, code):
    if not settings.DEFAULT_FROM_EMAIL:
        raise EmailDeliveryError("Email delivery is not configured.")
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        raise EmailDeliveryError("Only the configured SMTP email backend is permitted.")
    if "\r" in settings.DEFAULT_FROM_EMAIL or "\n" in settings.DEFAULT_FROM_EMAIL:
        raise EmailDeliveryError("The sender address is invalid.")
    try:
        sender_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
        validate_email(sender_address)
    except ValidationError as exc:
        raise EmailDeliveryError("The sender address is invalid.") from exc
    if not settings.EMAIL_HOST or not 1 <= settings.EMAIL_PORT <= 65535:
        raise EmailDeliveryError("Email delivery is not configured.")
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        raise EmailDeliveryError("Email transport settings are invalid.")
    if bool(settings.EMAIL_HOST_USER) != bool(settings.EMAIL_HOST_PASSWORD):
        raise EmailDeliveryError("Email credentials are incomplete.")

    minutes = settings.EMAIL_VERIFICATION_EXPIRY_MINUTES
    safe_code = escape(code)
    subject = "Verify your CineSplit email"
    text_body = (
        "Welcome to CineSplit.\n\n"
        f"Your email verification code is {code}.\n"
        f"It expires in {minutes} minutes.\n\n"
        "If you did not create a CineSplit account, you can ignore this email."
    )
    html_body = f"""<!doctype html>
<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;background:#0b0b0c;color:#f2f0ed;font-family:Arial,sans-serif">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0b0b0c;padding:36px 16px">
    <tr><td align="center"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#151516;border:1px solid #292827;border-radius:14px">
      <tr><td style="padding:36px 32px;text-align:center">
        <div style="color:#cfaa72;font-size:13px;font-weight:bold;letter-spacing:3px">CINESPLIT</div>
        <h1 style="font-size:25px;line-height:1.3;margin:28px 0 12px">Verify your email</h1>
        <p style="color:#b6b2ae;font-size:15px;line-height:1.6;margin:0">Use this code to finish creating your account.</p>
        <div aria-label="Verification code" style="display:inline-block;margin:26px 0;padding:16px 24px;border:1px solid #504331;border-radius:10px;color:#e2c18f;font-size:32px;font-weight:bold;letter-spacing:10px">{safe_code}</div>
        <p style="color:#b6b2ae;font-size:14px;line-height:1.6">This code expires in {minutes} minutes.</p>
        <p style="color:#817e7a;font-size:12px;line-height:1.6;margin:26px 0 0">If you did not register for CineSplit, ignore this message.</p>
      </td></tr></table></td></tr>
  </table>
</body></html>"""
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient])
    message.attach_alternative(html_body, "text/html")
    try:
        sent = message.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError, BadHeaderError) as exc:
        logger.warning("Verification email delivery failed (%s).", type(exc).__name__)
        raise EmailDeliveryError("Verification email delivery failed.") from exc
    if sent != 1:
        logger.warning("Verification email delivery returned no accepted recipients.")
        raise EmailDeliveryError("Verification email delivery failed.")
