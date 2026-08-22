"""
models/product.py
------------------
Represents a single item in the shop catalog.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Product:
    id: Optional[int]
    sku: str
    name: str
    description: Optional[str]
    price_cents: int
    currency: str
    is_active: bool
    image_path: Optional[str] = None
    icon_key: Optional[str] = None
    created_at: str = ""
    updated_at: Optional[str] = None
