from flask_login import current_user
from models.emergency_information import EmergencyInformation
import extensions as ext

def owns_record(record:EmergencyInformation) -> bool:
    """Return True if the current user owns the emergency information record."""
    if not current_user.is_authenticated:
        return False
    return record.user_id == current_user.id


def can_view_record(record:EmergencyInformation) -> bool:
    return ext.permission_manager.is_admin() or owns_record(record)


def can_edit_record(record:EmergencyInformation) -> bool:
    return ext.permission_manager.is_admin() or owns_record(record)


def can_delete_record(record:EmergencyInformation) -> bool:
    return ext.permission_manager.is_admin() or owns_record(record)


def can_regenerate_token(record:EmergencyInformation) -> bool:
    return ext.permission_manager.is_admin() or owns_record(record)


def can_toggle_active(record:EmergencyInformation) -> bool:
    """Only admins can force-disable a record."""
    return ext.permission_manager.is_admin()