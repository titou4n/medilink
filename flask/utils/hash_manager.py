from werkzeug.security import generate_password_hash
from hashlib import blake2b

import hashlib
import hmac
import logging
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)


class HashManager():
    """
    Provides password hashing, verification and HMAC utilities.

    No state is stored; the class is a thin namespace for related
    functions so it can be injected and mocked in tests.
    """

    # ------------------------------------------------------------------ #
    # Password helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_password_hash(plain_password: str) -> str:
        return generate_password_hash(plain_password)

    @staticmethod
    def check_password(plain_password: str, password_hash: str) -> bool:
        """
        Return ``True`` if *plain_password* matches *password_hash*.

        Wraps :func:`werkzeug.security.check_password_hash` so callers
        never import werkzeug directly.
        """
        return check_password_hash(password_hash, plain_password)

    # ------------------------------------------------------------------ #
    # General-purpose HMAC helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def hmac_sha256(value: str, secret: str) -> str:
        """
        Return the hex-encoded HMAC-SHA256 of *value* keyed with *secret*.

        Used to hash session IDs, IP addresses and user-agents before
        storing them in the database.
        """
        return hmac.new(
            secret.encode("utf-8"),
            value.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def sha256(value: str) -> str:
        """Return the hex-encoded SHA-256 digest of *value*."""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ #
    # Token generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_secure_token(nbytes: int = 32) -> str:
        """Return a URL-safe, cryptographically random token string."""
        return secrets.token_urlsafe(nbytes)

    @staticmethod
    def generate_numeric_otp(digits: int = 6) -> str:
        """Return a zero-padded numeric OTP of *digits* length."""
        upper_bound = 10 ** digits
        return str(secrets.randbelow(upper_bound)).zfill(digits)