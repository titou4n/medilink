# blueprints/settings/routes.py
# Préfixe : /settings  (défini dans create_app)

from flask import render_template, redirect, request, flash, url_for, send_file, abort
from flask_login import login_required, current_user

from blueprints.settings import bp
from blueprints.settings.services import build_data_export, save_profile_picture
from utils.decorators import require_permission
import extensions as ext


# ── Hub settings ────────────────────────────────────────────────────────────

@bp.route('', methods=['GET', 'POST'])
@bp.route('/', methods=['GET', 'POST'])
@login_required
def settings_home():
    return render_template('settings/settings_home.html',
                           id=current_user.id,
                           name=ext.db_account_repository.get_name_by_id(current_user.id))


# ── Compte ──────────────────────────────────────────────────────────────────

@bp.route('/account', methods=['GET', 'POST'])
@bp.route('/account/', methods=['GET', 'POST'])
@login_required
@require_permission("view_own_profile")
def account_home():
    return render_template('settings/account_home.html',
                           id=current_user.id,
                           name=current_user.name,
                           email=current_user.email,
                           email_verified=current_user.email_verified,
                           role_name=current_user.role_name)


@bp.route('/account/change_email', methods=['GET', 'POST'])
@bp.route('/account/change_email/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def account_change_email():
    if request.method == 'GET':
        return render_template('settings/account_change_email.html',
                               id=current_user.id,
                               user_has_email=(current_user.email is not None),
                               email=current_user.email)

    email = request.form.get("email", "").strip().lower()
    is_valid, error = ext.email_manager.validate_user_email(email)

    if not is_valid:
        flash(error, "error")
        return redirect(url_for('settings.account_change_email'))

    if email != current_user.email and ext.db_account_repository.exists_by_email(email):
        flash("This email is already used by another account.", "error")
        return redirect(url_for('settings.account_change_email'))

    ext.db_account_repository.update_email(current_user.id, email)
    ext.db_account_repository.update_email_verified(current_user.id, False)
    flash('Your email has been updated')
    return redirect(url_for('settings.account_home'))


@bp.route('/account/change_password', methods=['GET', 'POST'])
@bp.route('/account/change_password/', methods=['GET', 'POST'])
@login_required
@require_permission("change_own_password")
def account_change_password():
    if request.method == 'GET':
        return render_template('settings/account_change_password.html', id=current_user.id)

    actual_password    = str(request.form['actual_password'])
    new_password       = str(request.form['new_password'])
    verif_new_password = str(request.form['verif_new_password'])

    stored_hash = ext.db_account_repository.get_password_hash(current_user.id)
    if not ext.hash_manager.check_password(actual_password, stored_hash):
        flash('Password is not correct.')
        return redirect(url_for('settings.account_change_password'))

    if new_password != verif_new_password:
        flash("Passwords must be identical.")
        return redirect(url_for('settings.account_change_password'))

    password_error = ext.utils.validate_password_strength(new_password, ext.config.MIN_PASSWORD_LENGTH)
    if password_error:
        flash(password_error)
        return redirect(url_for('settings.account_change_password'))

    ext.db_account_repository.update_password(current_user.id, ext.hash_manager.generate_password_hash(new_password))
    ext.session_manager.logout_other_sessions(current_user.id)
    flash('Your password has been updated')
    return redirect(url_for('settings.account_home'))


@bp.route('/account/change_name', methods=['GET', 'POST'])
@bp.route('/account/change_name/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def account_change_name():
    if request.method == 'GET':
        return render_template('settings/account_change_name.html',
                               id=current_user.id,
                               name=ext.db_account_repository.get_name_by_id(current_user.id))

    new_name = str(request.form['new_name']).strip()
    if not new_name:
        flash('Name is required !')
        return redirect(url_for('settings.account_change_name'))

    if len(new_name) > ext.config.MAX_SHORT_FIELD:
        flash(f'Name must not exceed {ext.config.MAX_SHORT_FIELD} characters.')
        return redirect(url_for('settings.account_change_name'))

    if ext.db_account_repository.exists_by_name(new_name):
        flash('This name is already taken !')
        return redirect(url_for('settings.account_change_name'))

    ext.db_account_repository.update_name(current_user.id, new_name)
    flash('Your name has been updated')
    return redirect(url_for('settings.account_home'))


@bp.route('/account/delete_account', methods=['GET', 'POST'])
@bp.route('/account/delete_account/', methods=['GET', 'POST'])
@login_required
@require_permission("delete_own_account")
def delete_account():
    if request.method == 'GET':
        return redirect(url_for('settings.account_home'))

    ext.db_account_repository.delete(current_user.id)
    ext.session_manager.logout()
    flash('Your account was successfully deleted!')
    return redirect('/')


@bp.route('/account/upload_profile_picture', methods=['GET', 'POST'])
@bp.route('/account/upload_profile_picture/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def upload_profile_picture():
    if request.method == 'GET':
        return redirect(url_for('settings.account_home'))

    file = request.files.get('profile_picture')
    save_profile_picture(current_user.id, file)
    return redirect(url_for('settings.account_home'))


@bp.route('/profile_picture/<int:user_id>')
@login_required
def profile_picture(user_id: int):
    path = ext.db_account_repository.get_profile_picture_path(user_id)
    if not path or not __import__('os').path.isfile(path):
        path = ext.config.PATH_DEFAULT_PROFILE_PICTURE
    return send_file(path)


# ── Sécurité ─────────────────────────────────────────────────────────────────

@bp.route('/security', methods=['GET', 'POST'])
@bp.route('/security/', methods=['GET', 'POST'])
@login_required
def security_home():
    email    = ext.db_account_repository.get_email_by_id(current_user.id)
    sessions = ext.db_session_repository.get_all_by_user_id(user_id=current_user.id)

    return render_template('settings/security_home.html',
                           id=current_user.id,
                           name=ext.db_account_repository.get_name_by_id(current_user.id),
                           user_has_email=email is not None,
                           email=email,
                           email_verified=ext.db_account_repository.get_email_verified_by_id(current_user.id),
                           twofa_enabled=ext.db_account_repository.get_twofa_enabled(user_id=current_user.id),
                           session_id_hash=ext.session_manager.get_current_session_id_hash(),
                           session_location=ext.session_manager.get_location(),
                           ip_address=ext.session_manager.get_ip_session(),
                           sessions=sessions)


@bp.route('/switch_2fa', methods=['GET', 'POST'])
@bp.route('/switch_2fa/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def settings_switch_2fa():
    if request.method == 'GET':
        return redirect(url_for('settings.security_home'))

    if ext.db_account_repository.get_email_by_id(current_user.id) is None:
        flash("Please add an email address first.")
        return redirect(url_for('settings.account_change_email'))

    if not ext.db_account_repository.get_email_verified_by_id(current_user.id):
        flash("Please verify your email address first - Click on 'Verify-it' link.")
        return redirect(url_for('settings.security_home'))

    ext.db_account_repository.toggle_twofa(user_id=current_user.id)
    flash('Your preferences has been updated')
    return redirect(url_for('settings.security_home'))


@bp.route('/logout_all', methods=['POST'])
@bp.route('/logout_all/', methods=['POST'])
@login_required
def settings_logout_all():
    ext.session_manager.logout_user_from_all_devices(user_id=current_user.id)
    return redirect('/')


@bp.route('/logout_session/<string:session_id_hash>', methods=['POST'])
@login_required
def settings_logout_session(session_id_hash: str):
    if not ext.session_manager.logout_session_owned(session_id_hash=session_id_hash, user_id=current_user.id):
        abort(403)
    return redirect(url_for('settings.security_home'))


@bp.route('/delete_session/<string:session_id_hash>', methods=['POST'])
@login_required
def settings_delete_session(session_id_hash: str):
    if not ext.session_manager.delete_session_owned(session_id_hash=session_id_hash, user_id=current_user.id):
        abort(403)
    return redirect(url_for('settings.security_home'))


# ── Notifications ────────────────────────────────────────────────────────────

@bp.route('/notifications', methods=['GET', 'POST'])
@bp.route('/notifications/', methods=['GET', 'POST'])
@login_required
def notifications_home():
    return render_template('settings/notifications_home.html', id=current_user.id)


@bp.route('/notify_password_change', methods=['GET', 'POST'])
@bp.route('/notify_password_change/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def settings_notify_password_change():
    flash("Not Implemented")
    return redirect(url_for('settings.notifications_home'))


@bp.route('/notify_twofa_change', methods=['GET', 'POST'])
@bp.route('/notify_twofa_change/', methods=['GET', 'POST'])
@login_required
@require_permission("edit_own_profile")
def settings_notify_twofa_change():
    flash("Not Implemented")
    return redirect(url_for('settings.notifications_home'))


# ── Vie privée ───────────────────────────────────────────────────────────────

@bp.route('/privacy', methods=['GET', 'POST'])
@bp.route('/privacy/', methods=['GET', 'POST'])
@login_required
def privacy_home():
    return render_template('settings/privacy_home.html', id=current_user.id)


@bp.route('/privacy/export_data', methods=['GET', 'POST'])
@bp.route('/privacy/export_data/', methods=['GET', 'POST'])
@login_required
@require_permission("export_own_data")
def export_data():
    file = build_data_export(current_user.id)
    return send_file(file, mimetype='text/plain', as_attachment=True,
                     download_name=f'export_data_{current_user.id}.txt')


# ── Apparence ────────────────────────────────────────────────────────────────

@bp.route('/appearance', methods=['GET', 'POST'])
@bp.route('/appearance/', methods=['GET', 'POST'])
@login_required
def appearance_home():
    return render_template('settings/appearance_home.html', id=current_user.id)


# ── About / Support ──────────────────────────────────────────────────────────

@bp.route('/about_support', methods=['GET', 'POST'])
@bp.route('/about_support/', methods=['GET', 'POST'])
@login_required
def about_support_home():
    return render_template('settings/about_support_home.html', id=current_user.id)
