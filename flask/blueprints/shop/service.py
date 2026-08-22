"""
blueprints/shop/service.py
-----------------------------
Business logic for the product catalog and the shopping cart.

Security invariant: every price, name and availability check here re-reads
the ``products`` table - a cart operation or a checkout never trusts a
price, product name or quantity coming from the client. The client only
ever supplies a product sku/id and a desired quantity; everything else is
resolved server-side.
"""

import logging
import mimetypes
import os
import secrets
from dataclasses import dataclass
from typing import Optional

from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename

from Data.repositories.product_repository import ProductRepository
from Data.repositories.cart_repository import CartRepository
from models.product import Product
from models.cart import Cart, CartItem
import extensions as ext

logger = logging.getLogger(__name__)

# Upper bound on how many units of a single product one cart line can hold -
# not a business requirement, just a sane guardrail against typos/abuse
# (e.g. a client sending quantity=999999).
MAX_ITEM_QUANTITY = 20


@dataclass
class CartOperationResult:
    ok: bool
    message: str


# ---------------------------------------------------------------------- #
# Product image upload
#
# Mirrors blueprints/settings/services.py::validate_profile_picture /
# save_profile_picture: extension + MIME + magic-byte + Pillow-decode
# validation, a random unpredictable filename, and re-encoding the image
# (pixels only) instead of writing the uploaded bytes as-is, which strips
# any extra data a polyglot/malicious file might carry beyond what PIL
# actually decodes as an image.
#
# Unlike profile pictures, product images are public catalog content, so
# the path stored in DB is a path relative to the static folder (e.g.
# "uploads/product_images/xxx.png") and is served directly via
# url_for('static', ...) instead of a dedicated access-controlled route.
# ---------------------------------------------------------------------- #

def validate_product_image(file) -> tuple[bool, str]:
    """Validate an uploaded product image file."""

    if not file or file.filename == '':
        return False, "No file provided"

    filename = secure_filename(file.filename)
    if not filename or '.' not in filename:
        return False, "Invalid filename"

    allowed_extensions = current_app.config.get("ALLOWED_EXTENSIONS_PRODUCT_IMAGE", {'png', 'jpg', 'jpeg'})
    ext_name = filename.rsplit('.', 1)[1].lower()
    if ext_name not in allowed_extensions:
        return False, f"File extension not allowed: {ext_name}"

    file.seek(0)
    mime_type = file.mimetype or mimetypes.guess_type(filename)[0]
    allowed_mimes = {'image/png', 'image/jpeg'}
    if mime_type not in allowed_mimes:
        return False, f"Invalid MIME type: {mime_type}"

    file.seek(0)
    header = file.read(8)
    if not (
        (header[:4] == b'\x89PNG') or  # PNG
        (header[:2] == b'\xff\xd8')    # JPEG
    ):
        return False, "Invalid image file (magic bytes)"

    file.seek(0)
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except Exception as e:
        return False, f"Corrupted image file: {str(e)}"

    file.seek(0, 2)
    file_size = file.tell()
    max_size = current_app.config.get("PRODUCT_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    if file_size > max_size:
        return False, f"File too large: {file_size} bytes (max: {max_size})"

    file.seek(0)
    return True, ""


def _product_image_disk_path(relative_path: str) -> str:
    return os.path.join(current_app.static_folder, relative_path)


def _delete_product_image_file(relative_path: Optional[str]) -> None:
    if not relative_path:
        return
    disk_path = _product_image_disk_path(relative_path)
    if os.path.exists(disk_path):
        try:
            os.remove(disk_path)
        except Exception as e:
            logger.warning("Failed to delete product image file %s: %s", disk_path, str(e))


def save_product_image(product_id: int, file) -> bool:
    """Validate, save and associate an image with a product, replacing any previous one."""

    is_valid, error_msg = validate_product_image(file)
    if not is_valid:
        logger.warning("Invalid product image upload attempt for product %s: %s", product_id, error_msg)
        return False

    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    new_filename = f"product_{product_id}_{secrets.token_hex(8)}.{extension}"

    folder = current_app.config['UPLOAD_PRODUCT_IMAGE_FOLDER']
    filepath = os.path.join(folder, new_filename)

    try:
        file.seek(0)
        img = Image.open(file)
        if extension in ("jpg", "jpeg"):
            img = img.convert("RGB")
            save_format = "JPEG"
        else:  # png
            img = img.convert("RGBA")
            save_format = "PNG"
        img.save(filepath, format=save_format)
    except Exception as e:
        logger.warning("Failed to re-encode product image for product %s: %s", product_id, str(e))
        return False

    old_product = ext.db_product_repository.get_by_id(product_id)
    old_relative_path = old_product["image_path"] if old_product else None

    relative_path = f"uploads/product_images/{new_filename}"
    ext.db_product_repository.update_image_path(product_id, relative_path)

    _delete_product_image_file(old_relative_path)

    logger.info("Image uploaded for product %s", product_id)
    return True


def delete_product_image(product_id: int) -> None:
    """Remove a product's custom image, reverting it to the default display."""
    product = ext.db_product_repository.get_by_id(product_id)
    if not product:
        return

    _delete_product_image_file(product["image_path"])
    ext.db_product_repository.update_image_path(product_id, None)
    logger.info("Image removed for product %s", product_id)


class ProductService:
    """Service layer for the shop catalog."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def _row_to_model(self, row) -> Product:
        return Product(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            description=row["description"],
            price_cents=row["price_cents"],
            currency=row["currency"],
            is_active=bool(row["is_active"]),
            image_path=row["image_path"],
            icon_key=row["icon_key"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_active_catalog(self) -> list[Product]:
        return [self._row_to_model(r) for r in self._repository.get_all_active()]

    def get_by_id(self, product_id: int) -> Optional[Product]:
        row = self._repository.get_by_id(product_id)
        return self._row_to_model(row) if row else None

    def get_by_sku(self, sku: str) -> Optional[Product]:
        row = self._repository.get_by_sku(sku)
        return self._row_to_model(row) if row else None

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        result = self._repository.get_all_paginated(page, per_page)
        result["items"] = [self._row_to_model(r) for r in result["items"]]
        return result

    def sku_exists(self, sku: str, exclude_id: Optional[int] = None) -> bool:
        return self._repository.sku_exists(sku, exclude_id)

    # ------------------------------------------------------------------ #
    # Admin writes
    # ------------------------------------------------------------------ #

    def create_product(
        self,
        sku: str,
        name: str,
        description: str,
        price_cents: int,
        currency: str,
        icon_key: Optional[str] = None,
    ) -> Product:
        product_id = self._repository.create(sku, name, description or None, price_cents, currency, icon_key)
        return self.get_by_id(product_id)

    def update_product(
        self,
        product_id: int,
        name: str,
        description: str,
        price_cents: int,
        icon_key: Optional[str] = None,
    ) -> None:
        """
        Update *name*/*description*/*price_cents*/*icon_key* - currency is
        fixed for the whole catalog (see config.SHOP_CURRENCY) and sku is
        immutable once created, since it may already be referenced by past
        order_items snapshots. The product image is managed separately (see
        save_product_image/delete_product_image) since it involves a file,
        not just a DB column.
        """
        self._repository.update(product_id, name, description or None, price_cents, icon_key)

    def set_active(self, product_id: int, is_active: bool) -> None:
        self._repository.set_active(product_id, is_active)


class CartService:
    """Service layer for the persistent, per-user shopping cart."""

    def __init__(self, cart_repository: CartRepository, product_repository: ProductRepository) -> None:
        self._carts = cart_repository
        self._products = product_repository

    def _item_row_to_model(self, row) -> CartItem:
        product = Product(
            id=row["product_id"],
            sku=row["product_sku"],
            name=row["product_name"],
            description=row["product_description"],
            price_cents=row["product_price_cents"],
            currency=row["product_currency"],
            is_active=bool(row["product_is_active"]),
        )
        return CartItem(id=row["id"], cart_id=row["cart_id"], product=product, quantity=row["quantity"])

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_cart(self, user_id: int) -> Cart:
        cart_row = self._carts.get_or_create_cart(user_id)
        items = [self._item_row_to_model(r) for r in self._carts.get_items(cart_row["id"])]
        return Cart(
            id=cart_row["id"],
            user_id=user_id,
            created_at=cart_row["created_at"],
            updated_at=cart_row["updated_at"],
            items=items,
        )

    def get_item_count(self, user_id: int) -> int:
        return self._carts.count_items(user_id)

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    def add_item(self, user_id: int, product_sku: str, quantity: int) -> CartOperationResult:
        if quantity < 1:
            return CartOperationResult(False, "Quantity must be at least 1.")

        product_row = self._products.get_by_sku(product_sku)
        if not product_row or not product_row["is_active"]:
            return CartOperationResult(False, "This product is not available.")

        cart_row = self._carts.get_or_create_cart(user_id)

        existing = self._carts.get_item_by_product(cart_row["id"], product_row["id"])
        current_qty = existing["quantity"] if existing else 0
        if current_qty + quantity > MAX_ITEM_QUANTITY:
            return CartOperationResult(False, f"You can have at most {MAX_ITEM_QUANTITY} of this item in your cart.")

        self._carts.add_item(cart_row["id"], product_row["id"], quantity)
        logger.info("Cart: user %d added sku=%s qty=%d", user_id, product_sku, quantity)
        return CartOperationResult(True, f"{product_row['name']} added to your cart.")

    def update_quantity(self, user_id: int, item_id: int, quantity: int) -> CartOperationResult:
        if quantity < 1 or quantity > MAX_ITEM_QUANTITY:
            return CartOperationResult(False, f"Quantity must be between 1 and {MAX_ITEM_QUANTITY}.")

        cart_row = self._carts.get_or_create_cart(user_id)
        item_row = self._carts.get_item(cart_row["id"], item_id)
        if not item_row:
            return CartOperationResult(False, "This item is not in your cart.")

        self._carts.update_quantity(cart_row["id"], item_id, quantity)
        return CartOperationResult(True, "Quantity updated.")

    def remove_item(self, user_id: int, item_id: int) -> CartOperationResult:
        cart_row = self._carts.get_or_create_cart(user_id)
        item_row = self._carts.get_item(cart_row["id"], item_id)
        if not item_row:
            return CartOperationResult(False, "This item is not in your cart.")

        self._carts.remove_item(cart_row["id"], item_id)
        return CartOperationResult(True, "Item removed from your cart.")

    def clear(self, user_id: int) -> None:
        cart_row = self._carts.get_or_create_cart(user_id)
        self._carts.clear(cart_row["id"])
