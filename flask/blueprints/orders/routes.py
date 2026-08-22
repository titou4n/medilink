"""
Routes for orders.

URL map:
  GET  /orders/               -> redirect to the shop catalog (see blueprints/shop)
  POST /orders/create         -> create a pending order from the current user's cart
  GET  /orders/mine           -> the current user's order history
  GET  /orders/<id>           -> order detail (owner or admin only)
  POST /orders/<id>/pay       -> create a Stripe Checkout Session and redirect to it
  POST /orders/<id>/cancel    -> cancel a pending order (owner only)
  POST /orders/webhook/stripe -> Stripe webhook receiver (no auth - signature-verified)
  GET  /orders/admin/               -> admin: paginated list of every order
  POST /orders/admin/<id>/advance   -> admin: move a paid order to its next fulfillment status
  POST /orders/admin/<id>/refund    -> admin: refund a paid order via Stripe
"""
import logging
from flask import render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from blueprints.orders import bp
from blueprints.orders.permissions import can_view_order, owns_order
from utils.decorators import require_permission, require_admin
from utils.stripe_manager import StripeManagerError
from utils.url_helper import build_external_url
import extensions as ext

logger = logging.getLogger(__name__)


@bp.route('/')
@bp.route('')
@login_required
@require_permission("orders_access")
def catalog():
    return redirect(url_for('shop.catalog'))


@bp.route('/create', methods=['POST'])
@ext.limiter.limit("10 per hour")
@login_required
@require_permission("orders_access")
def create():
    cart = ext.cart_service.get_cart(current_user.id)
    if cart.is_empty:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop.cart_view'))

    try:
        order = ext.order_service.create_pending_order_from_cart(current_user.id, cart)
    except Exception as e:
        logger.error("Error creating order for user %s: %s", current_user.id, str(e))
        flash('An error occurred while creating your order. Please try again.', 'error')
        return redirect(url_for('shop.cart_view'))

    if order is None:
        flash('The item(s) in your cart are no longer available.', 'error')
        return redirect(url_for('shop.cart_view'))

    ext.cart_service.clear(current_user.id)
    flash('Your order has been created.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@bp.route('/mine')
@bp.route('/mine/')
@login_required
@require_permission("orders_access")
def mine():
    orders = ext.order_service.get_all_for_user(current_user.id)
    return render_template('orders/list.html', orders=orders)


@bp.route('/<int:order_id>')
@bp.route('/<int:order_id>/')
@login_required
@require_permission("orders_access")
def detail(order_id: int):
    order = ext.order_service.get_by_id(order_id)
    if not order:
        abort(404)
    if not can_view_order(order):
        abort(403)

    # `just_paid` only ever comes from our own Stripe success_url (see pay()
    # below) - it's a display hint, never proof of payment. The real status
    # shown is always order.status, read fresh from the DB, which only a
    # verified webhook (see stripe_webhook()) can move to "paid".
    just_paid = request.args.get('just_paid') == '1'
    attempt = request.args.get('attempt', 0, type=int)
    max_polling_attempts = 5
    still_confirming = just_paid and order.status == 'pending'

    return render_template(
        'orders/detail.html',
        order=order,
        stripe_enabled=ext.config.STRIPE_ENABLED,
        just_paid=just_paid,
        still_confirming=still_confirming,
        polling=still_confirming and attempt < max_polling_attempts,
        next_poll_url=url_for('orders.detail', order_id=order.id, just_paid=1, attempt=attempt + 1),
        is_admin=ext.permission_manager.is_admin(),
        next_fulfillment_status=ext.order_service.next_fulfillment_status(order.status),
        is_refundable=ext.order_service.is_refundable(order.status),
    )


@bp.route('/<int:order_id>/pay', methods=['POST'])
@bp.route('/<int:order_id>/pay/', methods=['POST'])
@ext.limiter.limit("20 per hour")
@login_required
@require_permission("orders_access")
def pay(order_id: int):
    order = ext.order_service.get_by_id(order_id)
    if not order:
        abort(404)
    if not can_view_order(order):
        abort(403)

    if not ext.config.STRIPE_ENABLED:
        flash('Online payment is not available yet.', 'error')
        return redirect(url_for('orders.detail', order_id=order.id))

    if order.status != 'pending':
        flash('This order can no longer be paid.', 'warning')
        return redirect(url_for('orders.detail', order_id=order.id))

    success_url = build_external_url(url_for('orders.detail', order_id=order.id, just_paid=1))
    cancel_url = build_external_url(url_for('orders.detail', order_id=order.id))

    try:
        session = ext.stripe_manager.create_checkout_session(
            order,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except StripeManagerError:
        flash('Unable to start payment right now. Please try again later.', 'error')
        return redirect(url_for('orders.detail', order_id=order.id))

    ext.order_service.attach_checkout_session(order.id, session.id)
    return redirect(session.url, code=303)


@bp.route('/<int:order_id>/cancel', methods=['POST'])
@ext.limiter.limit("20 per hour")
@login_required
@require_permission("orders_access")
def cancel(order_id: int):
    """
    Cancel a pending order - owner only, never available once it's paid.

    A paid order can never reach this branch even if the client forges the
    request: the status check below reads order.status fresh from the DB,
    which only a verified Stripe webhook can ever move to 'paid'.
    """
    order = ext.order_service.get_by_id(order_id)
    if not order:
        abort(404)
    if not owns_order(order):
        abort(403)

    if order.status != 'pending':
        flash('Only orders awaiting payment can be cancelled.', 'warning')
        return redirect(url_for('orders.detail', order_id=order.id))

    if order.stripe_checkout_session_id:
        try:
            ext.stripe_manager.expire_checkout_session(order.stripe_checkout_session_id)
        except StripeManagerError:
            # Best-effort: the order is cancelled either way - see
            # StripeManager.expire_checkout_session for why a failure here
            # (e.g. the session was already completed/expired) isn't fatal.
            logger.info("Could not expire Stripe session for cancelled order %d", order.id)

    if not ext.order_service.cancel_order(order.id):
        # Lost a race with a Stripe webhook that just marked this order paid
        # (see OrderService.cancel_order) - it must not be reported as
        # cancelled since it no longer is.
        flash('This order was just confirmed as paid and can no longer be cancelled.', 'warning')
        return redirect(url_for('orders.detail', order_id=order.id))

    flash('Your order has been cancelled.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@bp.route('/webhook/stripe', methods=['POST'])
@ext.csrf.exempt
@ext.limiter.limit("120 per minute")
def stripe_webhook():
    """
    Receive and apply Stripe webhook events.

    Not behind @login_required/@require_permission - Stripe is not a logged-in
    MediLink user. Trust comes entirely from the signature check below, which
    is why this is the one route in the app exempted from CSRF protection:
    Stripe can't carry our CSRF cookie/token, and doesn't need to - the
    signature already proves the request is genuinely from Stripe.
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')

    try:
        event = ext.stripe_manager.construct_webhook_event(payload, sig_header)
    except StripeManagerError:
        return '', 400

    is_new = ext.order_service.record_webhook_event(event['id'], event['type'])
    if not is_new:
        logger.info("Webhook: duplicate event %s ignored", event['id'])
        return '', 200

    try:
        if event['type'] == 'checkout.session.completed':
            ext.order_service.mark_paid_from_checkout_session(event['data']['object'])
        elif event['type'] == 'checkout.session.expired':
            ext.order_service.notify_payment_failed_from_expired_session(event['data']['object'])
    except Exception:
        # The event is already recorded as "seen" - without un-recording it,
        # Stripe's automatic retry of this same event would hit the
        # idempotency guard above and be skipped forever, permanently losing
        # whatever it was supposed to apply. Returning 5xx tells Stripe to
        # retry; forgetting the event lets that retry actually reprocess it.
        logger.exception("Unhandled error processing Stripe webhook event %s", event['id'])
        ext.order_service.forget_webhook_event(event['id'])
        return '', 500

    return '', 200


@bp.route('/admin/<int:order_id>/advance', methods=['POST'])
@bp.route('/admin/<int:order_id>/advance/', methods=['POST'])
@ext.limiter.limit("60 per hour")
@login_required
@require_admin
def admin_advance(order_id: int):
    order = ext.order_service.get_by_id(order_id)
    if not order:
        abort(404)

    result = ext.order_service.advance_fulfillment(order.id)
    flash(result.message, 'success' if result.ok else 'warning')
    return redirect(url_for('orders.detail', order_id=order.id))


@bp.route('/admin/<int:order_id>/refund', methods=['POST'])
@bp.route('/admin/<int:order_id>/refund/', methods=['POST'])
@ext.limiter.limit("20 per hour")
@login_required
@require_admin
def admin_refund(order_id: int):
    order = ext.order_service.get_by_id(order_id)
    if not order:
        abort(404)

    if not ext.order_service.is_refundable(order.status):
        flash('This order cannot be refunded.', 'warning')
        return redirect(url_for('orders.detail', order_id=order.id))

    if not order.stripe_payment_intent_id:
        flash('No Stripe payment is on record for this order.', 'error')
        return redirect(url_for('orders.detail', order_id=order.id))

    try:
        ext.stripe_manager.refund_payment(order.stripe_payment_intent_id)
    except StripeManagerError:
        flash('Unable to refund this payment right now. Please try again later.', 'error')
        return redirect(url_for('orders.detail', order_id=order.id))

    result = ext.order_service.mark_refunded(order.id)
    if result.ok:
        ext.email_manager.send_order_refunded_email(
            user_id=order.user_id,
            order_id=order.id,
            total_amount_cents=order.total_amount_cents,
            currency=order.currency,
        )
        flash('Order refunded.', 'success')
    else:
        # The Stripe refund already went through even though our own status
        # write lost a race - not silently swallowed: the order stays
        # visibly out of sync (still e.g. 'paid') for a human to reconcile.
        flash(f"Payment was refunded via Stripe, but the order status update failed: {result.message}", 'warning')
    return redirect(url_for('orders.detail', order_id=order.id))


@bp.route('/admin')
@bp.route('/admin/')
@login_required
@require_admin
def admin_dashboard():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    pagination = ext.order_service.get_all_paginated(page=page, per_page=ext.config.ADMIN_PAGE_SIZE)
    return render_template(
        'orders/admin_dashboard.html',
        pagination=pagination,
        entries=pagination.get('items', []),
    )
