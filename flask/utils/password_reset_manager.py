import datetime
import logging

import extensions as ext

logger = logging.getLogger(__name__)


class PasswordResetManager:
    """
    Admin-triggered password reset flow.

    An admin never sees or sets the user's password: a single-use,
    time-limited token is generated, only its hash is stored, and a
    reset link is emailed to the account's own address. The user picks
    their new password themselves via that link.
    """

    def __init__(self):
        self.db_password_reset = ext.db_password_reset_repository
        self.db_account = ext.db_account_repository
        self.email_manager = ext.email_manager
        self.hash_manager = ext.hash_manager
        self.config = ext.config

    def request_reset(self, user_id: int) -> bool:
        """
        Generate a reset token for *user_id* and email the reset link.

        Any previously pending token for this user is invalidated first,
        so only the most recently requested link works. Returns True if
        the email was sent successfully.
        """
        token = self.hash_manager.generate_secure_token()
        token_hash = self.hash_manager.sha256(token)

        self.db_password_reset.delete_by_user_id(user_id=user_id)
        self.db_password_reset.insert(
            user_id=user_id,
            token_hash=token_hash,
            created_at=ext.utils.get_datetime_isoformat(),
        )

        return self.email_manager.send_password_reset_link_email(user_id=user_id, token=token)

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
