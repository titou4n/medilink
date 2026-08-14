# blueprints/auth/routes.py

import logging
from flask import render_template, redirect, request, flash, url_for, session as flask_session
from flask_login import current_user, login_user

from blueprints.auth import bp
from blueprints.auth.services import authenticate_user, register_user, authenticate_or_create_google_user
import extensions as ext
from models.user import User
from utils.twofa_manager import (
    TwoFactorCodeNotFoundError, TwoFactorCodeAlreadyUsedError,
    TwoFactorTooManyAttemptsError, TwoFactorCodeExpiredError,
    TwoFactorInvalidCodeError
)

logger = logging.getLogger(__name__)


@bp.route('/login', methods=['GET', 'POST'])
@bp.route('/login/', methods=['GET', 'POST'])
@ext.limiter.limit("5 per minute; 20 per hour; 100 per day")
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    email = request.form.get('email', '').strip()
    raw_password = request.form.get('password', '').strip()

    if not email or not raw_password:
        flash('Email and password are required.')
        return redirect(url_for('auth.login'))

    user_id, error = authenticate_user(email, raw_password)
    if error:
        flash(error)
        return redirect(url_for('auth.login'))

    # Créer une session temporaire (sans accès full à l'app)
    ext.session_manager.send_temp_2fa_session(user_id=user_id)

    if ext.db_account_repository.get_twofa_enabled(user_id=user_id):
        return redirect(url_for('auth.two_factor_authentication'))

    # Si pas de 2FA, créer la session réelle
    try:
        user = User(user_id)
        login_user(user)
        ext.session_manager.finalize_2fa_session(user_id)
        logger.info("User %s logged in successfully (no 2FA)", user_id)
        return redirect(url_for('main.home'))
    except Exception as e:
        logger.error("Error loading user %s: %s", user_id, str(e))
        flash('An error occurred during login. Please try again.')
        return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@bp.route('/register/', methods=['GET', 'POST'])
@ext.limiter.limit("3 per minute; 10 per hour; 30 per day")
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')

    email = request.form.get('email', '').strip()
    raw_password = request.form.get('password', '').strip()
    raw_verif = request.form.get('verif_password', '').strip()

    if not all([email, raw_password, raw_verif]):
        flash('All fields are required.')
        return redirect(url_for('auth.register'))

    user_id, error = register_user(email=email, raw_password=raw_password, raw_verif=raw_verif, name=email)
    if error:
        flash(error)
        return redirect(url_for('auth.register'))

    logger.info("User %s registered successfully", user_id)
    return redirect(url_for('main.home'))


@bp.route('/login/google')
@bp.route('/login/google/')
def google_login():
    if not ext.config.GOOGLE_OAUTH_ENABLED:
        flash('Google sign-in is not available.')
        return redirect(url_for('auth.login'))

    redirect_uri = url_for('auth.google_callback', _external=True)
    return ext.oauth.google.authorize_redirect(redirect_uri)


@bp.route('/login/google/callback')
@bp.route('/login/google/callback/')
def google_callback():
    if not ext.config.GOOGLE_OAUTH_ENABLED:
        flash('Google sign-in is not available.')
        return redirect(url_for('auth.login'))

    try:
        token = ext.oauth.google.authorize_access_token()
    except Exception as e:
        logger.warning("Google OAuth callback failed: %s", str(e))
        flash('Google sign-in failed. Please try again.')
        return redirect(url_for('auth.login'))

    claims = token.get('userinfo')
    if not claims:
        logger.warning("Google OAuth callback: no userinfo/ID token claims in token response")
        flash('Google sign-in failed. Please try again.')
        return redirect(url_for('auth.login'))

    user_id, error = authenticate_or_create_google_user(claims)
    if error:
        flash(error)
        return redirect(url_for('auth.login'))

    # Même pipeline que le login classique : session temporaire -> 2FA si activée -> session réelle.
    ext.session_manager.send_temp_2fa_session(user_id=user_id)

    if ext.db_account_repository.get_twofa_enabled(user_id=user_id):
        return redirect(url_for('auth.two_factor_authentication'))

    try:
        user = User(user_id)
        login_user(user)
        ext.session_manager.finalize_2fa_session(user_id)
        logger.info("User %s logged in successfully via Google (no 2FA)", user_id)
        return redirect(url_for('main.home'))
    except Exception as e:
        logger.error("Error loading user %s: %s", user_id, str(e))
        flash('An error occurred during login. Please try again.')
        return redirect(url_for('auth.login'))


@bp.route('/forgot_password', methods=['GET', 'POST'])
@bp.route('/forgot_password/', methods=['GET', 'POST'])
@ext.limiter.limit("2 per minute")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'GET':
        return render_template('auth/forgot_password.html')

    email = request.form.get('email', '').strip()
    if not email:
        flash('Email is required.')
        return render_template('auth/forgot_password.html')

    user_id = ext.db_account_repository.get_id_by_email(email=email)

    if user_id is None:
        logger.warning("Password reset attempt with non-existent email: %s", email)
        flash("If this account exists and email is verified, you will receive a password reset link.")
        return render_template('auth/forgot_password.html')
    
    user_email = ext.db_account_repository.get_email_by_id(user_id)
    if not user_email:
        logger.warning("Password reset attempt for user without email: %s", user_id)
        flash("If this account exists and email is verified, you will receive a password reset link.")
        return render_template('auth/forgot_password.html')

    if not ext.db_account_repository.get_email_verified_by_id(user_id=user_id):
        logger.warning("Password reset attempt for user without email verified: %s", user_id)
        flash("If this account exists and email is verified, you will receive a password reset link.")
        return render_template('auth/forgot_password.html')

    try:
        new_password = ext.utils.generate_password(size=ext.config.PASSWORD_GENERATION_LENGTH)
        ext.db_account_repository.update_password(
            user_id=user_id,
            new_password_hash=ext.hash_manager.generate_password_hash(new_password)
        )
        ext.email_manager.send_new_password_code_with_html(user_id=user_id, new_password=new_password)
        hidden_email = ext.email_manager.get_hide_email(user_id=user_id)
        flash(f"An email containing a new password has been sent to {hidden_email or 'your email address'}.")
        logger.info("Password reset requested for user %s", user_id)
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error("Error processing password reset: %s", str(e))
        flash('An error occurred. Please try again later.')
        return render_template('auth/forgot_password.html')


@bp.route('/two_factor_authentication', methods=['GET', 'POST'])
@bp.route('/two_factor_authentication/', methods=['GET', 'POST'])
@ext.limiter.limit("10 per minute")
def two_factor_authentication():
    if current_user.is_authenticated:
        user_id = current_user.id

    else:
        temp_user_id = flask_session.get("temp_user_id")

        if temp_user_id is None:
            flash("Unauthorized access", "error")
            return redirect(url_for('auth.login'))
        
        user_id = int(temp_user_id)

    ext.db_twofa_repository.delete_expired()

    if request.method == 'GET':
        if ext.twofa_manager.verif_need_to_sent_new_code(user_id=user_id):
            ext.db_twofa_repository.delete_by_user_id(user_id=user_id)
            ext.twofa_manager.send_code(user_id=user_id)

        hidden_email = ext.email_manager.get_hide_email(user_id=user_id)
        flash(f"An email containing a two-factor authentication code has been sent to: {hidden_email or 'your email address'}")
        return render_template('auth/two_factor_authentication.html')

    code = request.form.get('code', '').strip()
    if not code:
        flash("Code is required.", "error")
        return redirect(url_for('auth.two_factor_authentication'))

    try:
        ext.twofa_manager.verif_code(code, user_id)
        flash("Your two-factor authentication was successful.")

        # Créer la session réelle maintenant
        user = User(user_id)
        login_user(user)
        ext.session_manager.finalize_2fa_session(user_id)

        logger.info("2FA verified for user %s", user_id)
        return redirect(url_for("main.home"))

    except TwoFactorCodeNotFoundError:
        flash("Invalid or expired code.", "error")
    except TwoFactorCodeAlreadyUsedError:
        flash("This code was already used.", "error")
    except TwoFactorTooManyAttemptsError:
        flash("Too many attempts. Request a new code.", "error")
    except TwoFactorCodeExpiredError:
        flash("Invalid or expired code.", "error")
    except TwoFactorInvalidCodeError:
        flash("Invalid or expired code.", "error")
    except Exception as e:
        logger.error("Unexpected error during 2FA: %s", str(e))
        flash("An error occurred. Please try again.", "error")

    return redirect(url_for("auth.two_factor_authentication"))
