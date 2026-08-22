"""
QR code generation for the public emergency link.

The QR code only ever encodes the existing public URL (token-based,
see token_generator.py) — never medical or personal data.
"""

import io
from urllib.parse import urlparse

import segno

# Print-quality settings: large enough scale for A4/card printing while
# keeping the mandatory quiet zone (border) for reliable scanning.
_SCALE = 10
_BORDER = 4
_DARK = "#0f172a"   # matches --color-text, high contrast on white
_LIGHT = "#ffffff"


def _validate_url(url: str) -> None:
    """Defensive check: only ever encode an http(s) URL, nothing else."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("QR code payload must be a valid http(s) URL.")


def generate_qr_png(url: str) -> bytes:
    """Render the given URL as a PNG QR code and return the raw bytes."""
    _validate_url(url)
    qr = segno.make(url, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=_SCALE, border=_BORDER, dark=_DARK, light=_LIGHT)
    return buffer.getvalue()


def generate_qr_svg(url: str) -> bytes:
    """Render the given URL as an SVG QR code and return the raw bytes."""
    _validate_url(url)
    qr = segno.make(url, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=_SCALE, border=_BORDER, dark=_DARK)
    return buffer.getvalue()


def generate_qr_data_uri(url: str) -> str:
    """Render the given URL as a QR code and return it as a PNG data URI, for inline embedding (e.g. the print page)."""
    _validate_url(url)
    qr = segno.make(url, error="m")
    return qr.png_data_uri(scale=_SCALE, border=_BORDER, dark=_DARK, light=_LIGHT)
