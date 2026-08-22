"""
Routes for the shop: product catalog + shopping cart.

URL map:
  GET  /shop/                              -> product catalog (active products)
  POST /shop/cart/add                      -> add a product to the current user's cart, then redirect to the cart
  GET  /shop/cart                          -> view the current user's cart
  POST /shop/cart/items/<item_id>/update   -> change a cart line's quantity
  POST /shop/cart/items/<item_id>/remove   -> remove a cart line
  GET  /shop/admin/products                -> admin: paginated product list
  GET  /shop/admin/products/create         -> admin: create a product
  GET  /shop/admin/products/<id>/edit      -> admin: edit a product
  POST /shop/admin/products/<id>/activate  -> admin: re-list a product
  POST /shop/admin/products/<id>/deactivate-> admin: de-list a product

Every cart route below resolves the cart from `current_user.id` server-side
and never from anything supplied by the client - so there is no request
parameter that could ever point at another user's cart.
"""
import logging
from flask import render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from blueprints.shop import bp
from blueprints.shop.service import save_product_image, delete_product_image
from utils.decorators import require_permission
import extensions as ext

logger = logging.getLogger(__name__)


def _clean_icon_key(raw_icon_key: str) -> str | None:
    """Whitelist the submitted icon key; anything unrecognised falls back to the default icon."""
    icon_key = (raw_icon_key or '').strip()
    if icon_key in ext.config.PRODUCT_ICON_CHOICES:
        return icon_key
    return None


# ---------------------------------------------------------------------- #
# Catalog
# ---------------------------------------------------------------------- #

@bp.route('/')
@bp.route('')
@login_required
@require_permission("orders_access")
def catalog():
    products = ext.product_service.get_active_catalog()
    return render_template('shop/catalog.html', products=products, currency=ext.config.SHOP_CURRENCY)


# ---------------------------------------------------------------------- #
# Cart
# ---------------------------------------------------------------------- #

@bp.route('/cart/add', methods=['POST'])
@ext.limiter.limit("60 per hour")
@login_required
@require_permission("orders_access")
def cart_add():
    sku = request.form.get('sku', '').strip()
    quantity = request.form.get('quantity', 1, type=int)

    if not sku or quantity is None:
        flash('Invalid product or quantity.', 'error')
        return redirect(url_for('shop.catalog'))

    result = ext.cart_service.add_item(current_user.id, sku, quantity)
    flash(result.message, 'success' if result.ok else 'error')
    if not result.ok:
        return redirect(url_for('shop.catalog'))
    return redirect(url_for('shop.cart_view'))


@bp.route('/cart')
@bp.route('/cart/')
@login_required
@require_permission("orders_access")
def cart_view():
    cart = ext.cart_service.get_cart(current_user.id)
    return render_template('shop/cart.html', cart=cart, currency=ext.config.SHOP_CURRENCY)


@bp.route('/cart/items/<int:item_id>/update', methods=['POST'])
@ext.limiter.limit("60 per hour")
@login_required
@require_permission("orders_access")
def cart_item_update(item_id: int):
    quantity = request.form.get('quantity', type=int)
    if quantity is None:
        flash('Invalid quantity.', 'error')
        return redirect(url_for('shop.cart_view'))

    result = ext.cart_service.update_quantity(current_user.id, item_id, quantity)
    if not result.ok:
        flash(result.message, 'error')
    return redirect(url_for('shop.cart_view'))


@bp.route('/cart/items/<int:item_id>/remove', methods=['POST'])
@ext.limiter.limit("60 per hour")
@login_required
@require_permission("orders_access")
def cart_item_remove(item_id: int):
    result = ext.cart_service.remove_item(current_user.id, item_id)
    flash(result.message, 'success' if result.ok else 'error')
    return redirect(url_for('shop.cart_view'))


# ---------------------------------------------------------------------- #
# Admin: product management
# ---------------------------------------------------------------------- #

@bp.route('/admin/products')
@bp.route('/admin/products/')
@login_required
@require_permission("access_admin_panel")
@require_permission("manage_products")
def admin_products():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    pagination = ext.product_service.get_all_paginated(page=page, per_page=ext.config.ADMIN_PAGE_SIZE)
    return render_template(
        'admin/admin_products.html',
        pagination=pagination,
        products=pagination.get('items', []),
    )


@bp.route('/admin/products/create', methods=['GET', 'POST'])
@bp.route('/admin/products/create/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("manage_products")
def admin_product_create():
    if request.method == 'GET':
        return render_template(
            'admin/admin_create_product.html',
            currency=ext.config.SHOP_CURRENCY,
            icon_choices=ext.config.PRODUCT_ICON_CHOICES,
        )

    sku = request.form.get('sku', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price = request.form.get('price', type=float)
    icon_key = _clean_icon_key(request.form.get('icon_key', ''))

    if not sku or not name or price is None or price <= 0:
        flash('Please fill in a valid sku, name and price.', 'warning')
        return redirect(url_for('shop.admin_product_create'))

    if ext.product_service.sku_exists(sku):
        flash('A product with this SKU already exists.', 'error')
        return redirect(url_for('shop.admin_product_create'))

    price_cents = round(price * 100)
    product = ext.product_service.create_product(
        sku, name, description, price_cents, ext.config.SHOP_CURRENCY, icon_key
    )

    image = request.files.get('image')
    if image and image.filename:
        if not save_product_image(product.id, image):
            flash('Product created, but the image could not be saved (invalid or unsupported file).', 'warning')

    flash('Product created.', 'success')
    return redirect(url_for('shop.admin_products'))


@bp.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@bp.route('/admin/products/<int:product_id>/edit/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("manage_products")
def admin_product_edit(product_id: int):
    product = ext.product_service.get_by_id(product_id)
    if not product:
        abort(404)

    if request.method == 'GET':
        return render_template(
            'admin/admin_edit_product.html',
            product=product,
            icon_choices=ext.config.PRODUCT_ICON_CHOICES,
        )

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price = request.form.get('price', type=float)
    icon_key = _clean_icon_key(request.form.get('icon_key', ''))

    if not name or price is None or price <= 0:
        flash('Please fill in a valid name and price.', 'warning')
        return redirect(url_for('shop.admin_product_edit', product_id=product_id))

    price_cents = round(price * 100)
    ext.product_service.update_product(product_id, name, description, price_cents, icon_key)

    image = request.files.get('image')
    if image and image.filename:
        if not save_product_image(product_id, image):
            flash('Product updated, but the image could not be saved (invalid or unsupported file).', 'warning')
    elif request.form.get('remove_image'):
        delete_product_image(product_id)

    flash('Product updated.', 'success')
    return redirect(url_for('shop.admin_products'))


@bp.route('/admin/products/<int:product_id>/deactivate', methods=['POST'])
@bp.route('/admin/products/<int:product_id>/deactivate/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("manage_products")
def admin_product_deactivate(product_id: int):
    product = ext.product_service.get_by_id(product_id)
    if not product:
        abort(404)

    ext.product_service.set_active(product_id, False)
    flash(f'"{product.name}" was removed from the shop.', 'success')
    return redirect(url_for('shop.admin_products'))


@bp.route('/admin/products/<int:product_id>/activate', methods=['POST'])
@bp.route('/admin/products/<int:product_id>/activate/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("manage_products")
def admin_product_activate(product_id: int):
    product = ext.product_service.get_by_id(product_id)
    if not product:
        abort(404)

    ext.product_service.set_active(product_id, True)
    flash(f'"{product.name}" is back in the shop.', 'success')
    return redirect(url_for('shop.admin_products'))
