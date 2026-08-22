from flask_login import current_user
from models.order import Order
import extensions as ext


def owns_order(order: Order) -> bool:
    """Return True if the current user owns *order*."""
    if not current_user.is_authenticated:
        return False
    return order.user_id == current_user.id


def can_view_order(order: Order) -> bool:
    return ext.permission_manager.is_admin() or owns_order(order)
