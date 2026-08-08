# blueprints/auth/services.py
# Logique métier auth : isolée des routes pour faciliter les tests.

import logging
import extensions as ext
from models.user import User
from flask_login import login_user

logger = logging.getLogger(__name__)


def authenticate_user(email: str, raw_password: str):
    """
    Authentifie un utilisateur.
    Retourne (user_id, error_message).
    error_message est None si succès.
    """
    AUTHENTICATION_ERROR_MESSAGE = "Invalid email or password."

    if not email or not raw_password:
        logger.warning("Authentication attempt with empty email or password.")
        return None, AUTHENTICATION_ERROR_MESSAGE

    user_id = ext.db_account_repository.get_id_by_email(email)
    if user_id is None:
        logger.warning("Authentication failed: no account for the given email")
        return None, AUTHENTICATION_ERROR_MESSAGE

    stored_hash = ext.db_account_repository.get_password_hash(user_id)
    if not stored_hash:
        logger.error("No password hash found for user %s", user_id)
        return None, AUTHENTICATION_ERROR_MESSAGE

    if not ext.hash_manager.check_password(raw_password, stored_hash):
        logger.warning("Authentication failed: invalid password for user %s", user_id)
        return None, AUTHENTICATION_ERROR_MESSAGE

    if ext.db_account_repository.get_is_active_by_id(user_id) is False:
        logger.warning("Authentication blocked: account %s is suspended", user_id)
        return None, "This account has been suspended. Please contact an administrator."

    try:
        ext.db_account_repository.insert_metadata(
            user_id=user_id,
            date_connected=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_ip_session()
        )
        logger.info("User %s authenticated successfully", user_id)
    except Exception as e:
        logger.error("Error inserting metadata for user %s: %s", user_id, str(e))

    return user_id, None


def register_user(email: str, raw_password: str, raw_verif: str, name: str):
    """
    Crée un compte.
    Retourne (user_id, error_message).
    """
    if not email or not raw_password or not raw_verif or not name:
        logger.warning("Registration attempt with missing fields")
        return None, "All fields are required."

    is_valid_email, email_error = ext.email_manager.validate_user_email(email)
    if not is_valid_email:
        logger.warning("Registration failed: invalid email format")
        return None, email_error

    if ext.db_account_repository.exists_by_email(email):
        logger.warning("Registration failed: email already exists")
        return None, "An account with this email already exists."

    if ext.db_account_repository.exists_by_name(name):
        logger.warning("Registration failed: name already exists")
        return None, "Name is already used."

    if raw_password != raw_verif:
        logger.warning("Registration failed: password mismatch")
        return None, "Passwords must be identical."

    password_error = ext.utils.validate_password_strength(raw_password, ext.config.MIN_PASSWORD_LENGTH)
    if password_error:
        logger.warning("Registration failed: weak password")
        return None, password_error

    try:
        password_hash = ext.hash_manager.generate_password_hash(raw_password)
        role_id = ext.db_role_repository.get_role_id(role_name="user")

        if role_id is None:
            logger.error("User role not found in database")
            return None, "System configuration error. Please try again later."

        ext.db_account_repository.create(email, password_hash, name, role_id)
        user_id = ext.db_account_repository.get_id_by_email(email)

        if user_id is None:
            logger.error("Failed to retrieve created user %s", user_id)
            return None, "Registration failed. Please try again."

        ext.session_manager.send_session(user_id=user_id)
        ext.db_account_repository.create_preferences(user_id=user_id)

        user = User(user_id)
        login_user(user)

        ext.db_account_repository.insert_metadata(
            user_id=user_id,
            date_connected=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_ip_session()
        )

        ext.email_manager.send_welcome_email(user_id=user_id)

        logger.info("User %s registered successfully", user_id)
        return user_id, None

    except Exception as e:
        logger.error("Error during registration: %s", str(e))
        return None, "Registration failed. Please try again."