import datetime
import logging

import extensions as ext

logger = logging.getLogger(__name__)


class EmailChangeManager:
    """
    Single-use, time-limited token + link email-change flow.

    Changing the email on file is a sensitive action: whoever controls that
    address can later receive password-reset links and 2FA codes for the
    account. So the new address is never written to ``account.email``
    immediately - a confirmation link is emailed to the *new* address first,
    and the change only takes effect once that link is opened, proving the
    account owner actually controls the mailbox they're switching to.
    """

    def __init__(self):
        self.db_email_change = ext.db_email_change_repository
        self.db_account = ext.db_account_repository
        self.db_session = ext.db_session_repository
        self.email_manager = ext.email_manager
        self.hash_manager = ext.hash_manager
        self.config = ext.config

    def request_change(self, user_id: int, new_email: str) -> bool:
        """
        Generate a confirmation token for *user_id* -> *new_email* and email
        the confirmation link to the new address.

        Any previously pending change for this user is invalidated first, so
        only the most recently requested link works. A heads-up notice is
        also sent to the *current* address on file, so the real owner is
        warned even if they weren't the one who requested the change.
        Returns True if the confirmation email was sent successfully.
        """
        token = self._create_token(user_id, new_email)

        try:
            self.email_manager.send_email_change_requested_notice(user_id=user_id, new_email=new_email)
        except Exception as e:
            logger.error("Error sending email-change heads-up notice for user %s: %s", user_id, str(e))

        return self.email_manager.send_email_change_confirmation_email(
            user_id=user_id, new_email=new_email, token=token
        )

    def _create_token(self, user_id: int, new_email: str) -> str:
        token = self.hash_manager.generate_secure_token()
        token_hash = self.hash_manager.sha256(token)

        self.db_email_change.delete_by_user_id(user_id=user_id)
        self.db_email_change.insert(
            user_id=user_id,
            new_email=new_email,
            token_hash=token_hash,
            created_at=ext.utils.get_datetime_isoformat(),
        )
        return token

    def verify_token(self, token: str) -> dict:
        """Return ``{"user_id": ..., "new_email": ...}`` for a valid, unused, unexpired *token*."""
        row = self._get_valid_row(token)
        return {"user_id": row["user_id"], "new_email": row["new_email"]}

    def confirm_change(self, token: str) -> int:
        """
        Validate *token*, apply the pending email change and invalidate the
        token.

        The new address is proven owned by the act of opening this link, so
        it's marked verified directly. Every existing session for the
        account is revoked - closing out any session that was open (and
        possibly hijacked) when the change was requested, not just the one
        that requested it. Returns the user_id whose email was changed.
        """
        row = self._get_valid_row(token)
        user_id = row["user_id"]
        new_email = row["new_email"]

        if self.db_account.exists_by_email(new_email):
            self.db_email_change.mark_as_used(id_email_change_tokens=row["id_email_change_tokens"])
            self.db_email_change.delete_by_user_id(user_id=user_id)
            raise EmailChangeEmailTakenError("This email is already used by another account.")

        self.db_email_change.mark_as_used(id_email_change_tokens=row["id_email_change_tokens"])
        self.db_account.update_email(user_id=user_id, email=new_email)
        self.db_account.update_email_verified(user_id=user_id, verified=True)
        self.db_email_change.delete_by_user_id(user_id=user_id)
        self.db_session.revoke_all_for_user(user_id=user_id)

        logger.info("Email change confirmed for user %s", user_id)
        return user_id

    def _get_valid_row(self, token: str):
        token_hash = self.hash_manager.sha256(token)
        row = self.db_email_change.get_by_token_hash(token_hash=token_hash)

        if row is None or row["used"]:
            raise EmailChangeTokenInvalidError("Invalid or expired email change link.")

        created_at = datetime.datetime.fromisoformat(row["created_at"])
        if ext.utils.datetime_is_expired_minutes(created_at, self.config.EMAIL_CHANGE_TOKEN_TIMELAPS_MINUTES):
            raise EmailChangeTokenInvalidError("Invalid or expired email change link.")

        return row


class EmailChangeTokenInvalidError(Exception):
    pass


class EmailChangeEmailTakenError(Exception):
    pass
