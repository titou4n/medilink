import logging
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import url_for
from markupsafe import escape

import extensions as ext
from utils.url_helper import build_external_url

logger = logging.getLogger(__name__)


class EmailManager:
    """
    Sends transactional emails and renders them with MediLink's visual identity.

    The colors/fonts/radii below are copied from static/css/style.css so emails
    stay visually consistent with the site — email clients can't read the app's
    stylesheet, so the values have to be duplicated inline instead of shared.
    """

    _FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

    _COLOR_BG = "#f8fafc"
    _COLOR_SURFACE = "#ffffff"
    _COLOR_BORDER = "#e2e8f0"
    _COLOR_TEXT = "#0f172a"
    _COLOR_TEXT_SECONDARY = "#475569"
    _COLOR_TEXT_MUTED = "#94a3b8"
    _COLOR_PRIMARY = "#1a56db"
    _COLOR_PRIMARY_LIGHT = "#eff4ff"
    _COLOR_DANGER = "#dc2626"
    _COLOR_DANGER_LIGHT = "#fef2f2"
    _COLOR_DANGER_BORDER = "#fecaca"
    _COLOR_WARNING = "#b45309"
    _COLOR_WARNING_LIGHT = "#fffbeb"
    _COLOR_WARNING_BORDER = "#fde68a"

    def __init__(self):
        self.db_account = ext.db_account_repository
        self.config = ext.config
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email_address = self.config.EMAIL_ADDRESS
        self.sender_email_password = self.config.EMAIL_APP_PASSWORD
        self.EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"r"@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$")

    def get_hide_email(self, user_id: int) -> str | None:
        try:
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)
            if not receiver_email_address:
                return None

            email = str(receiver_email_address).strip()
            if '@' not in email:
                logger.warning("Invalid email format for user %s", user_id)
                return None

            at_index = email.index('@')
            number_char_visible = 3
            visible = email[:number_char_visible]
            domain = email[at_index:]
            hidden_length = max(at_index - number_char_visible, 0)
            hidden = '*' * hidden_length

            return visible + hidden + domain
        except Exception as e:
            logger.error("Error hiding email for user %s: %s", user_id, str(e))
            return None

    # ------------------------------------------------------------------ #
    # SMTP delivery
    # ------------------------------------------------------------------ #

    def _deliver(self, receiver_email_address: str, message) -> None:
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.sender_email_address, self.sender_email_password)
            server.sendmail(self.sender_email_address, receiver_email_address, message.as_string())

    def send_email(self, receiver_email_address: str, subject: str, text: str) -> bool:
        try:
            if not receiver_email_address or not subject or not text:
                logger.warning("Missing required email parameters")
                return False

            message = MIMEText(text, "plain")
            message["Subject"] = subject
            message["From"] = self.sender_email_address
            message["To"] = receiver_email_address

            self._deliver(receiver_email_address, message)
            logger.info("Email sent successfully to %s", receiver_email_address)
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending email to %s: %s", receiver_email_address, str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error sending email to %s: %s", receiver_email_address, str(e))
            return False

    def send_email_with_html_content(self, user_id: int, subject: str, html_content: str) -> bool:
        try:
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)

            if not receiver_email_address:
                logger.warning("No email found for user %s", user_id)
                return False

            if not subject or not html_content:
                logger.warning("Missing email subject or content for user %s", user_id)
                return False

            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = self.sender_email_address
            message["To"] = receiver_email_address
            message.attach(MIMEText(html_content, "html"))

            self._deliver(receiver_email_address, message)
            logger.info("HTML email sent successfully to user %s", user_id)
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending HTML email to user %s: %s", user_id, str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error sending HTML email to user %s: %s", user_id, str(e))
            return False

    # ------------------------------------------------------------------ #
    # Shared layout — mirrors the site's design system (header, card,
    # footer) so every email looks like it belongs to MediLink.
    # ------------------------------------------------------------------ #

    def _layout(self, preheader: str, heading: str, body_html: str) -> str:
        year = datetime.now().year
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:{self._COLOR_BG}; font-family:{self._FONT_FAMILY};">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0;">{preheader}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{self._COLOR_BG};">
        <tr>
            <td align="center" style="padding:32px 16px;">
                <table role="presentation" width="100%" style="max-width:520px;" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="center" style="padding-bottom:24px; font-size:18px; font-weight:700; color:{self._COLOR_TEXT};">
                            MediLink
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:{self._COLOR_SURFACE}; border:1px solid {self._COLOR_BORDER}; border-radius:14px; padding:36px 32px; box-shadow:0 4px 12px rgba(15,23,42,0.08);">
                            <h1 style="margin:0 0 16px; font-size:22px; line-height:1.3; font-weight:700; color:{self._COLOR_TEXT};">{heading}</h1>
                            {body_html}
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding-top:24px; font-size:12px; line-height:1.6; color:{self._COLOR_TEXT_MUTED};">
                            This is an automated message from MediLink — please don't reply to it.<br>
                            &copy; {year} MediLink
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _paragraph(self, html: str) -> str:
        return f'<p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:{self._COLOR_TEXT_SECONDARY};">{html}</p>'

    def _code_box(self, value, font_size: int = 32, letter_spacing: str = "6px", break_all: bool = False) -> str:
        word_break = "word-break:break-all;" if break_all else "white-space:nowrap;"
        return f"""
        <div style="margin:24px 0; padding:18px; text-align:center; background-color:{self._COLOR_PRIMARY_LIGHT}; border-radius:10px;">
            <span style="font-family:'Courier New', monospace; font-size:{font_size}px; font-weight:700; letter-spacing:{letter_spacing}; color:{self._COLOR_PRIMARY}; {word_break}">{value}</span>
        </div>"""

    def _button(self, label: str, url: str) -> str:
        return f"""
        <div style="margin:24px 0; text-align:center;">
            <a href="{url}" style="display:inline-block; padding:12px 28px; background-color:{self._COLOR_PRIMARY}; color:#ffffff; font-size:15px; font-weight:600; text-decoration:none; border-radius:6px;">{label}</a>
        </div>"""

    def _notice(self, html: str, variant: str = "warning") -> str:
        palette = {
            "warning": (self._COLOR_WARNING_LIGHT, self._COLOR_WARNING_BORDER, self._COLOR_WARNING),
            "danger": (self._COLOR_DANGER_LIGHT, self._COLOR_DANGER_BORDER, self._COLOR_DANGER),
        }
        bg, border, text = palette.get(variant, palette["warning"])
        return f"""
        <div style="margin:16px 0 0; padding:14px 16px; background-color:{bg}; border:1px solid {border}; border-radius:10px; font-size:13.5px; line-height:1.5; color:{text};">
            {html}
        </div>"""

    def _get_display_name(self, user_id: int):
        name = self.db_account.get_name_by_id(user_id=user_id)
        return escape(name or "User")

    # ------------------------------------------------------------------ #
    # Transactional emails
    # ------------------------------------------------------------------ #

    def send_two_factor_authentication_code_with_html(self, user_id: int, code: int) -> bool:
        try:
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)
            if not receiver_email_address:
                logger.warning("No email found for 2FA code for user %s", user_id)
                return False

            name = self._get_display_name(user_id)
            reset_password_url = build_external_url(url_for('auth.forgot_password'))

            body_html = (
                self._paragraph(f"Hi {name},")
                + self._paragraph(
                    "Use the verification code below to finish signing in to MediLink. "
                    f"It expires in {self.config.TWOFA_TIMELAPS_MINUTES} minutes."
                )
                + self._code_box(escape(str(code)))
                + self._notice(
                    "Didn't try to sign in? Someone else may know your password. "
                    f'<a href="{reset_password_url}" style="color:{self._COLOR_WARNING}; font-weight:600;">Reset it now</a>. '
                    "MediLink staff will never ask you for this code.",
                    variant="warning",
                )
            )
            html_content = self._layout(
                preheader="Use this code to finish signing in to MediLink.",
                heading="Verify it's you",
                body_html=body_html,
            )

            subject = "Your MediLink verification code"
            result = self.send_email_with_html_content(user_id=user_id, subject=subject, html_content=html_content)
            if result:
                logger.info("2FA code email sent to user %s", user_id)
            return result
        except Exception as e:
            logger.error("Error sending 2FA email to user %s: %s", user_id, str(e))
            return False

    def send_new_password_code_with_html(self, user_id: int, new_password: str) -> bool:
        try:
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)
            if not receiver_email_address:
                logger.warning("No email found for password reset for user %s", user_id)
                return False

            name = self._get_display_name(user_id)
            login_url = build_external_url(url_for('auth.login'))

            body_html = (
                self._paragraph(f"Hi {name},")
                + self._paragraph(
                    "We received a request to reset the password for your MediLink account. "
                    "Your new temporary password is below."
                )
                + self._code_box(escape(new_password), font_size=18, letter_spacing="0.5px", break_all=True)
                + self._button("Log in to MediLink", login_url)
                + self._paragraph("For your security, please change this password as soon as you log in.")
                + self._notice(
                    "If you didn't request this, your account may be at risk. "
                    "Log in and change your password immediately.",
                    variant="danger",
                )
            )
            html_content = self._layout(
                preheader="A new password was generated for your MediLink account.",
                heading="Your new password",
                body_html=body_html,
            )

            subject = "Your new MediLink password"
            result = self.send_email_with_html_content(user_id=user_id, subject=subject, html_content=html_content)
            if result:
                logger.info("Password reset email sent to user %s", user_id)
            return result
        except Exception as e:
            logger.error("Error sending password reset email to user %s: %s", user_id, str(e))
            return False

    def send_welcome_email(self, user_id: int) -> bool:
        try:
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)
            if not receiver_email_address:
                logger.warning("No email found for welcome email for user %s", user_id)
                return False

            name = self._get_display_name(user_id)
            dashboard_url = build_external_url(url_for('main.home'))

            body_html = (
                self._paragraph(f"Hi {name},")
                + self._paragraph(
                    "Welcome to MediLink. We help you keep your emergency medical information "
                    "ready and accessible for the people who may need it."
                )
                + self._button("Go to MediLink", dashboard_url)
                + self._paragraph(
                    "Two things worth doing right away: turn on two-factor authentication in "
                    "Settings &rsaquo; Security, and fill in your emergency information."
                )
            )
            html_content = self._layout(
                preheader="Your MediLink account is ready.",
                heading="Welcome to MediLink",
                body_html=body_html,
            )

            subject = "Welcome to MediLink"
            result = self.send_email_with_html_content(user_id=user_id, subject=subject, html_content=html_content)
            if result:
                logger.info("Welcome email sent to user %s", user_id)
            return result
        except Exception as e:
            logger.error("Error sending welcome email to user %s: %s", user_id, str(e))
            return False

    def validate_user_email(self, email: str) -> tuple[bool, str]:
        """
        Validate an email address.
        Returns:
            tuple[bool, str]:
                (True, "") if valid
                (False, error_message) otherwise
        """

        if not isinstance(email, str):
            return False, "Email is required"

        email = email.strip().lower()
        if not email:
            return False, "Email is required"

        if len(email) > 254:
            return False, "Email too long"

        if email.count("@") != 1:
            return False, "Invalid email format"

        local_part, domain_part = email.split("@")

        # RFC limits
        if len(local_part) > 64:
            return False, "Email local part too long"

        if len(domain_part) > 253:
            return False, "Email domain too long"

        if not self.EMAIL_REGEX.fullmatch(email):
            return False, "Invalid email format"

        # Prevent malformed domains
        if ".." in domain_part:
            return False, "Invalid domain"

        if domain_part.startswith("-") or domain_part.endswith("-"):
            return False, "Invalid domain"

        return True, ""
