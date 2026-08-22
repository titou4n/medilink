# blueprints/auth/services.py
# Logique métier auth : isolée des routes pour faciliter les tests.

import logging
import extensions as ext

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


def register_user(email: str, raw_password: str, raw_verif: str, name: str, terms_accepted: bool):
    """
    Crée un compte.
    Retourne (user_id, error_message).
    """
    if not email or not raw_password or not raw_verif or not name:
        logger.warning("Registration attempt with missing fields")
        return None, "All fields are required."

    if not terms_accepted:
        logger.warning("Registration failed: terms & conditions not accepted")
        return None, "You must accept the Terms & Conditions and Privacy Policy."

    is_valid_email, email_error = ext.email_manager.validate_user_email(email)
    if not is_valid_email:
        logger.warning("Registration failed: invalid email format")
        return None, email_error

    # Reclaim emails squatted by abandoned/unverified registrations before
    # checking uniqueness, so an attacker can't permanently block the real
    # owner from ever registering by signing up first and never verifying.
    ext.db_account_repository.delete_unverified_expired(ext.config.UNVERIFIED_ACCOUNT_TTL_MINUTES)

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

        ext.db_account_repository.create_preferences(user_id=user_id)

        # get_ip_session() resolves the IP via an existing `sessions` DB row,
        # which never exists yet at registration time (no login has happened) -
        # it would always return None here and crash on the ipv4 NOT NULL
        # constraint. get_client_ip() reads the request's IP directly instead.
        ext.db_account_repository.insert_metadata(
            user_id=user_id,
            date_connected=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_client_ip()
        )

        ext.db_account_repository.record_terms_consent(
            user_id=user_id,
            terms_version=ext.config.TERMS_VERSION,
            accepted_at=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_client_ip()
        )

        # Pas de session réelle tant que le compte n'est pas vérifié par 2FA.
        ext.session_manager.send_temp_2fa_session(user_id=user_id)

        ext.email_manager.send_welcome_email(user_id=user_id)

        logger.info("User %s registered successfully, awaiting 2FA verification", user_id)
        return user_id, None

    except Exception as e:
        logger.error("Error during registration: %s", str(e))
        return None, "Registration failed. Please try again."


def authenticate_or_create_google_user(claims: dict):
    """
    Resolve a verified Google OIDC login to a local account.

    Resolution order:
      1. An identity already linked to this Google account (``sub``) -> use it.
      2. No link yet, but an account already exists with the same, Google-
         verified email AND that account already independently proved
         ownership of the mailbox (``email_verified`` = True) -> auto-link.
         Google is trusted to own that mailbox, and the account has already
         proven the same through its own channel, so this cannot be used to
         take over an account you don't control.
      3. An account exists with that email but is still unverified -> it
         never proved ownership (e.g. someone signed up with this email and
         abandoned it before finishing verification, possibly an attacker
         squatting a victim's email). Google has just proven real ownership,
         so the unproven row is discarded and treated like case 4 below,
         instead of being silently linked/verified onto.
      4. No account at all -> create a brand new account, mirroring
         register_user() (role "user", name = email). The stored password
         hash is random and never handed to the user - Google is the only
         way to sign in to this account, exactly like accounts created
         through register_user() are keyed on a real password.

    Returns (user_id, error_message); error_message is None on success.
    """
    GOOGLE_ERROR_MESSAGE = "Google sign-in failed. Please try again."
    provider = "google"

    provider_sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    email_verified = bool(claims.get("email_verified"))

    if not provider_sub or not email:
        logger.warning("Google login: missing sub or email in ID token claims")
        return None, GOOGLE_ERROR_MESSAGE

    user_id = ext.db_oauth_identity_repository.get_account_id_by_provider_sub(
        provider=provider, provider_sub=provider_sub
    )

    if user_id is None:
        if not email_verified:
            logger.warning("Google login rejected: unverified email for sub=%s", provider_sub)
            return None, "Your Google account's email must be verified to sign in with Google."

        existing_user_id = ext.db_account_repository.get_id_by_email(email)
        existing_user_verified = (
            existing_user_id is not None
            and ext.db_account_repository.get_email_verified_by_id(existing_user_id)
        )

        if existing_user_id is not None and existing_user_verified:
            # The account already independently proved ownership of this
            # mailbox (own 2FA email code), and Google now proves it again -
            # safe to auto-link.
            ext.db_oauth_identity_repository.link(
                account_id=existing_user_id, provider=provider, provider_sub=provider_sub, email=email
            )
            user_id = existing_user_id
            logger.info("Linked Google identity to existing verified account %s", user_id)
        else:
            if existing_user_id is not None:
                # Unverified row for this email: nobody has proven ownership
                # through it, so it's not safe to silently link/verify onto -
                # it may be an account someone else squatted with the
                # victim's email. Google just proved real ownership, so
                # reclaim the email by discarding the unproven row and
                # creating a fresh, Google-owned account below.
                logger.warning(
                    "Google login reclaiming unverified account %s to prove email ownership",
                    existing_user_id,
                )
                ext.db_account_repository.delete(existing_user_id)

            try:
                role_id = ext.db_role_repository.get_role_id(role_name="user")
                if role_id is None:
                    logger.error("User role not found in database")
                    return None, "System configuration error. Please try again later."

                # Random, never-issued password: this account can only be
                # signed into through Google, but `account.password` stays
                # NOT NULL like every other row.
                random_password_hash = ext.hash_manager.generate_password_hash(
                    ext.hash_manager.generate_secure_token()
                )
                ext.db_account_repository.create(email, random_password_hash, email, role_id)

                user_id = ext.db_account_repository.get_id_by_email(email)
                if user_id is None:
                    logger.error("Failed to retrieve account just created from Google sign-in")
                    return None, GOOGLE_ERROR_MESSAGE

                ext.db_account_repository.update_email_verified(user_id, True)
                ext.db_account_repository.create_preferences(user_id=user_id)
                ext.db_oauth_identity_repository.link(
                    account_id=user_id, provider=provider, provider_sub=provider_sub, email=email
                )

                try:
                    ext.email_manager.send_welcome_email(user_id=user_id)
                except Exception as e:
                    logger.error("Error sending welcome email to Google-created user %s: %s", user_id, str(e))

                logger.info("Created new account %s via Google sign-in", user_id)
            except Exception as e:
                logger.error("Error creating account from Google sign-in: %s", str(e))
                return None, GOOGLE_ERROR_MESSAGE

    if ext.db_account_repository.get_is_active_by_id(user_id) is False:
        logger.warning("Google login blocked: account %s is suspended", user_id)
        return None, "This account has been suspended. Please contact an administrator."

    try:
        ext.db_account_repository.insert_metadata(
            user_id=user_id,
            date_connected=ext.utils.get_datetime_isoformat(),
            ipv4=ext.session_manager.get_ip_session()
        )
    except Exception as e:
        logger.error("Error inserting metadata for user %s: %s", user_id, str(e))

    return user_id, None