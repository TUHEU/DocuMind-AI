"""E-mail sending. Two backends:
- console (default): writes the recipient and subject to the log, sends nothing. Safe for development.
- smtp: sends through Brevo (smtp-relay.brevo.com, port 587, STARTTLS). Needs SMTP_LOGIN, SMTP_KEY and
  EMAIL_FROM (a sender verified in Brevo) in backend/.env. The key is never logged.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import Settings, get_settings

log = logging.getLogger("idp.email")


class EmailService:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()

    def send(self, to: str, subject: str, body: str) -> bool:
        """Return True if sent (or logged in console mode). Never raises: a mail problem must not break sign-up."""
        try:
            if self.s.email_backend == "smtp":
                return self._send_smtp(to, subject, body)
            log.info("EMAIL (console mode, not sent) to=%s subject=%s", to, subject)
            return True
        except Exception as exc:   # the message of the exception can contain the server reply, never the key
            log.error("E-mail to %s failed: %s", to, type(exc).__name__)
            return False

    def _send_smtp(self, to: str, subject: str, body: str) -> bool:
        s = self.s
        if not (s.smtp_login and s.smtp_key and s.email_from):
            log.error("SMTP selected but SMTP_LOGIN, SMTP_KEY or EMAIL_FROM is empty in .env")
            return False
        msg = EmailMessage()
        msg["From"] = f"{s.email_from_name} <{s.email_from}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(s.smtp_login, s.smtp_key)
            smtp.send_message(msg)
        log.info("EMAIL sent to=%s subject=%s", to, subject)
        return True


def get_email_service() -> EmailService:
    return EmailService()


def welcome_message(full_name: str) -> tuple[str, str]:
    return (
        "Welcome to DocuMind AI",
        f"Hello {full_name},\n\nYour DocuMind AI account has been created. You can now sign in.\n\n"
        "If you did not create this account, please ignore this message.\n",
    )
