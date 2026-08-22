import datetime
import logging

import extensions as ext

logger = logging.getLogger(__name__)


class PasswordResetManager:
    """
    Single-use, time-limited token + link password reset flow, shared by
    both entry points that can trigger it: an admin resetting another
    user's password from the admin panel, and a user resetting their own
    password via "Forgot my password".

    Neither the admin nor the app itself ever sees or sets the user's
    password: a random token is generated, only its hash is stored, and
    a reset link is emailed to the account's own address. The user picks
    their new password themselves via that link.
    """

    def __init__(self):
        self.db_password_reset = ext.db_password_reset_repository
        self.db_account = ext.db_account_repository
        self.email_manager = ext.email_manager
        self.hash_manager = ext.hash_manager
        self.config = ext.config

    def request_reset(self, user_id: int, self_service: bool = False) -> bool:
        """
        Generate a reset token for *user_id* and email the reset link.

        Any previously pending token for this user is invalidated first,
        so only the most recently requested link works. *self_service*
        selects the email wording: True for a user-initiated "Forgot my
        password" request, False (default) for an admin-triggered reset.
        Returns True if the email was sent successfully.
        """
        token = self._create_token(user_id)

        if self_service:
            return self.email_manager.send_self_service_password_reset_link_email(user_id=user_id, token=token)
        return self.email_manager.send_password_reset_link_email(user_id=user_id, token=token)

    def request_account_setup(self, user_id: int) -> bool:
        """
        Generate a reset token for a newly admin-created account and email
        a "set your password" link.

        Same single-use token mechanism as request_reset, reusing the same
        auth.reset_password route to consume it, but with wording suited to
        a first-time setup rather than a password reset. The account is
        created with an unusable random password hash, so this link is the
        only way to make it usable. Returns True if the email was sent.
        """
        token = self._create_token(user_id)
        return self.email_manager.send_account_setup_email(user_id=user_id, token=token)

    def _create_token(self, user_id: int) -> str:
        token = self.hash_manager.generate_secure_token()
        token_hash = self.hash_manager.sha256(token)

        self.db_password_reset.delete_by_user_id(user_id=user_id)
        self.db_password_reset.insert(
            user_id=user_id,
            token_hash=token_hash,
            created_at=ext.utils.get_datetime_isoformat(),
        )
        return token

    def verify_token(self, token: str) -> int:
        """Return the user_id for a valid, unused, unexpired *token*."""
        return self._get_valid_row(token)["user_id"]

    def consume_token(self, token: str, new_password_hash: str) -> int:
        """
        Validate *token*, apply *new_password_hash* and invalidate the token.

        Returns the user_id whose password was changed.
        """
        row = self._get_valid_row(token)
        user_id = row["user_id"]

        self.db_password_reset.mark_as_used(id_password_reset_tokens=row["id_password_reset_tokens"])
        self.db_account.update_password(user_id=user_id, new_password_hash=new_password_hash)
        self.db_password_reset.delete_by_user_id(user_id=user_id)

        logger.info("Password reset completed for user %s", user_id)
        return user_id

    def _get_valid_row(self, token: str):
        token_hash = self.hash_manager.sha256(token)
        row = self.db_password_reset.get_by_token_hash(token_hash=token_hash)

        if row is None or row["used"]:
            raise PasswordResetTokenInvalidError("Invalid or expired password reset link.")

        created_at = datetime.datetime.fromisoformat(row["created_at"])
        if ext.utils.datetime_is_expired_minutes(created_at, self.config.PASSWORD_RESET_TOKEN_TIMELAPS_MINUTES):
            raise PasswordResetTokenInvalidError("Invalid or expired password reset link.")

        return row


class PasswordResetTokenInvalidError(Exception):
    pass
