"""
Secure token generation utilities for public emergency links.
"""

import secrets
import extensions as ext


def generate_public_token() -> str:
    """
    Generate a cryptographically secure URL-safe token.
    Default: 48 random bytes → 96 hex characters, globally unique.
    """
    return secrets.token_hex(ext.config.TOKEN_LENGTH)


def build_public_url(token: str, base_url: str = '') -> str:
    """
    Construct the full public emergency URL for a given token.
    `base_url` should be the application's external root (e.g. https://example.com).
    """
    return f"{base_url.rstrip('/')}/emergency/{token}"
