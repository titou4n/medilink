import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from markupsafe import escape
import extensions as ext
import re

logger = logging.getLogger(__name__)


class EmailManager:
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

    def send_email(self, receiver_email_address: str, subject: str, text: str) -> bool:
        try:
            if not receiver_email_address or not subject or not text:
                logger.warning("Missing required email parameters")
                return False

            message = MIMEText(text, "plain")
            message["Subject"] = subject
            message["From"] = self.sender_email_address
            message["To"] = receiver_email_address

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender_email_address, self.sender_email_password)
                server.sendmail(
                    self.sender_email_address,
                    receiver_email_address,
                    message.as_string()
                )

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

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender_email_address, self.sender_email_password)
                server.sendmail(
                    self.sender_email_address,
                    receiver_email_address,
                    message.as_string()
                )

            logger.info("HTML email sent successfully to user %s", user_id)
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending HTML email to user %s: %s", user_id, str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error sending HTML email to user %s: %s", user_id, str(e))
            return False

    def send_two_factor_authentication_code_with_html(self, user_id: int, code: int) -> bool:
        try:
            name = self.db_account.get_name_by_id(user_id=user_id)
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)

            if not receiver_email_address:
                logger.warning("No email found for 2FA code for user %s", user_id)
                return False

            name = escape(name or "User")

            subject = "Two-factor authentication code"
            html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="margin:0; padding:0; font-family: Arial, sans-serif; background-color:#FAFAF8;">
            <div style="
                max-width:600px;
                margin:40px auto;
                padding:30px;
                background:#ffffff;
                border-radius:10px;
                box-shadow:0 4px 10px rgba(0,0,0,0.1);
                text-align:center;
            ">
                <h1 style="color:#9B7ED8;">Hello {name}</h1>

                <p style="font-size:16px; color:#333;">
                    Your two-factor authentication code:
                </p>

                <p style="
                    font-size:32px;
                    font-weight:bold;
                    letter-spacing:6px;
                    color:#9B7ED8;
                    margin:20px 0;
                ">
                    {escape(str(code))}
                </p>

                <p style="font-size:14px; color:#555;">
                    You recently tried to log in from a new device, browser, or location.
                    <br><br>
                    If this wasn't you, please change your password immediately.
                </p>

                <p style="font-size:12px; color:#999; margin-top:30px;">
                    - MediLink Security Team -
                </p>
            </div>
        </body>
        </html>
        """
            result = self.send_email_with_html_content(user_id=user_id, subject=subject, html_content=html_content)
            if result:
                logger.info("2FA code email sent to user %s", user_id)
            return result
        except Exception as e:
            logger.error("Error sending 2FA email to user %s: %s", user_id, str(e))
            return False

    def send_new_password_code_with_html(self, user_id: int, new_password: str) -> bool:
        try:
            name = self.db_account.get_name_by_id(user_id=user_id)
            receiver_email_address = self.db_account.get_email_by_id(user_id=user_id)

            if not receiver_email_address:
                logger.warning("No email found for password reset for user %s", user_id)
                return False

            name = escape(name or "User")

            subject = "New Password"
            html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="margin:0; padding:0; font-family: Arial, sans-serif; background-color:#FAFAF8;">
            <div style="
                max-width:600px;
                margin:40px auto;
                padding:30px;
                background:#ffffff;
                border-radius:10px;
                box-shadow:0 4px 10px rgba(0,0,0,0.1);
                text-align:center;
            ">
                <h1 style="color:#9B7ED8;">Hello {name}</h1>

                <p style="font-size:16px; color:#333;">
                    Here is your new password:
                </p>

                <p style="
                    font-size:20px;
                    font-weight:bold;
                    color:#9B7ED8;
                    margin:20px 0;
                ">
                    {escape(new_password)}
                </p>

                <p style="font-size:16px; color:#333;">
                    You can log in on the login page. Remember to change your password afterwards.
                </p>

                <p style="font-size:14px; color:#555;">
                    If this wasn't you, please change your password immediately.
                </p>

                <p style="font-size:12px; color:#999; margin-top:30px;">
                    - MediLink Security Team -
                </p>
            </div>
        </body>
        </html>
        """
            result = self.send_email_with_html_content(user_id=user_id, subject=subject, html_content=html_content)
            if result:
                logger.info("Password reset email sent to user %s", user_id)
            return result
        except Exception as e:
            logger.error("Error sending password reset email to user %s: %s", user_id, str(e))
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