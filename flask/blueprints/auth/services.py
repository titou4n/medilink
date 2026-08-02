# blueprints/auth/services.py
# Logique métier auth : isolée des routes pour faciliter les tests.

import logging
import extensions as ext
from models.user import User
from flask_login import login_user

logger = logging.getLogger(__name__)


def authenticate_user(username: str, raw_password: str):
    """
    Authentifie un utilisateur.
    Retourne (user_id, error_message).
    error_message est None si succès.
    """
    AUTHENTICATION_ERROR_MESSAGE = "Invalid username or password."

    if not username or not raw_password:
        logger.warning("Authentication attempt with empty username or password.")
        return None, AUTHENTICATION_ERROR_MESSAGE

    user_id = ext.db_account_repository.get_id_by_username(username)
    if user_id is None:
        logger.warning("Authentication failed: user not found (username not resolved to ID)")
        return None, AUTHENTICATION_ERROR_MESSAGE

    stored_hash = ext.db_account_repository.get_password_hash(user_id)
    if not stored_hash:
        logger.error("No password hash found for user %s", user_id)
        return None, AUTHENTICATION_ERROR_MESSAGE

    if not ext.hash_manager.check_password(raw_password, stored_hash):
        logger.warning("Authentication failed: invalid password for user %s", user_id)
        return None, AUTHENTICATION_ERROR_MESSAGE

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


def register_user(username: str, raw_password: str, raw_verif: str, name: str):
    """
    Crée un compte.
    Retourne (user_id, error_message).
    """
    if not username or not raw_password or not raw_verif or not name:
        logger.warning("Registration attempt with missing fields")
        return None, "All fields are required."

    if ext.db_account_repository.exists_by_username(username):
        logger.warning("Registration failed: username already exists")
        return None, "Username is already used."

    if ext.db_account_repository.exists_by_name(name):
        logger.warning("Registration failed: name already exists")
        return None, "Name is already used."

    if raw_password != raw_verif:
        logger.warning("Registration failed: password mismatch for username '%s'", username)
        return None, "Passwords must be identical."

    password_error = ext.utils.validate_password_strength(raw_password, ext.config.MIN_PASSWORD_LENGTH)
    if password_error:
        logger.warning("Registration failed: weak password for username '%s'", username)
        return None, password_error

    try:
        password_hash = ext.hash_manager.generate_password_hash(raw_password)
        role_id = ext.db_role_repository.get_role_id(role_name="user")

        if role_id is None:
            logger.error("User role not found in database")
            return None, "System configuration error. Please try again later."

        ext.db_account_repository.create(username, password_hash, name, role_id)
        user_id = ext.db_account_repository.get_id_by_username(username)

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

        logger.info("User %s registered successfully", user_id)
        return user_id, None

    except Exception as e:
        logger.error("Error during registration for user '%s': %s", username, str(e))
        return None, "Registration failed. Please try again."


def login_as_visitor():
    """
    Authentifie le compte visiteur pré-configuré.
    Retourne (user_id, error_message).
    """
    username = ext.config.USERNAME_VISITOR

    try:
        user_id = ext.db_account_repository.get_id_by_username(username)
        if user_id is None:
            logger.error("Visitor account '%s' not found in database", username)
            return None, "Visitor account not found."

        stored_hash = ext.db_account_repository.get_password_hash(user_id)
        if not stored_hash:
            logger.error("No password hash for visitor account %s", user_id)
            return None, "Visitor account misconfigured."

        if not ext.hash_manager.check_password(ext.config.PASSWORD_VISITOR, stored_hash):
            logger.error("Visitor account password mismatch")
            return None, "Visitor account misconfigured."

        ext.session_manager.send_session(user_id=user_id)
        user = User(user_id)
        login_user(user)

        ext.db_account_repository.insert_metadata(
            user_id=user_id,
            date_connected=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_ip_session()
        )

        logger.info("Visitor account logged in")
        return user_id, None

    except Exception as e:
        logger.error("Error logging in visitor account: %s", str(e))
        return None, "An error occurred. Please try again."
