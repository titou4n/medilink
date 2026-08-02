"""
Secure URL generation utilities.
Ensures URLs are generated from a validated, fixed configuration rather than
untrusted request headers to prevent Host Header Injection attacks.
"""

import logging
from urllib.parse import urlparse
import extensions as ext

logger = logging.getLogger(__name__)


def get_safe_base_url() -> str:
    """
    Retrieve the application's external base URL from configuration.
    This URL is used for generating external links (tokens, password resets, etc.)
    and is never derived from request.host to prevent Host Header Injection.

    Returns: Application base URL (e.g., 'https://medilink.ltjs.net')
    """
    base_url = ext.config.EXTERNAL_URL_BASE

    # Validate that the configured base URL's host is in ALLOWED_HOSTS
    parsed = urlparse(base_url)
    host = parsed.netloc.split(':')[0]  # Remove port if present

    if ext.config.ALLOWED_HOSTS and host not in ext.config.ALLOWED_HOSTS:
        logger.error(
            "EXTERNAL_URL_BASE host '%s' not in ALLOWED_HOSTS. "
            "Check configuration. Using configured URL anyway.",
            host
        )

    return base_url.rstrip('/')


def build_external_url(path: str) -> str:
    """
    Build a complete external URL for a given path.

    Args:
        path: The path to append (e.g., '/emergency/abc123' or '/auth/reset/token')

    Returns:
        Complete external URL (e.g., 'https://medilink.ltjs.net/emergency_information/public/abc123')
    """
    base = get_safe_base_url()
    path = path.lstrip('/')
    return f"{base}/{path}"
