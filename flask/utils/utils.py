"""
utils/utils.py
--------------
Generic helper utilities shared across the application.
"""

from datetime import datetime, timedelta, timezone
import logging
import secrets

logger = logging.getLogger(__name__)


class Utils:
    """Collection of application-level utility methods."""

    ############################################
    #_______________DATETIME___________________#
    ############################################

    @staticmethod
    def format_date(dt):
        """Format datetime to 'DD MMM YYYY' in local timezone."""
        if dt is None:
            return "—"

        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt

        return dt.astimezone().strftime("%d %b %Y")

    @staticmethod
    def format_datetime(dt):
        """Format datetime to 'DD MMM YYYY at HH:MM' in local timezone."""
        if dt is None:
            return "—"

        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt

        return dt.astimezone().strftime("%d %b %Y at %H:%M")

    @staticmethod
    def get_datetime_utc():
        """Return the current UTC-aware datetime."""
        return datetime.now(timezone.utc)

    @staticmethod
    def get_datetime_isoformat():
        """Return the current UTC datetime as an ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def datetime_is_expired_minutes(datetime_created, timedelta_minutes):
        """Check if datetime has expired by specified minutes."""
        return datetime.now(timezone.utc) > datetime_created + timedelta(minutes=timedelta_minutes)

    ############################################
    #_______________PASSWORD___________________#
    ############################################

    @staticmethod
    def generate_password(size: int) -> str:
        """Generate a URL-safe random password of given size."""
        return secrets.token_urlsafe(size)

    @staticmethod
    def validate_password_strength(password: str, min_length: int) -> str | None:
        """
        Validate a plaintext password server-side.
        Returns an error message if the password is too weak, ``None`` if it's acceptable.
        """
        if not password or len(password) < min_length:
            return f"Password must be at least {min_length} characters."
        return None

