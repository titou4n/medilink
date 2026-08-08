# blueprints/admin/routes.py
# Préfixe : /admin_panel  (défini dans create_app)

from flask import render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user

from blueprints.admin import bp
from blueprints.admin.services import (
    change_user_role, set_user_active_status, delete_user_account, create_user_account
)
from utils.decorators import require_permission
import extensions as ext


@bp.route('', methods=['GET'])
@bp.route('/', methods=['GET'])
@login_required
@require_permission("access_admin_panel")
def admin_panel():
    return render_template('admin/admin_panel.html',
                           id=current_user.id,
                           flask_env=ext.config.FLASK_ENV)


# ── Gestion des rôles ────────────────────────────────────────────────────────

@bp.route('/role_permission_manager', methods=['GET'])
@bp.route('/role_permission_manager/', methods=['GET'])
@login_required
@require_permission("access_admin_panel")
@require_permission("view_roles")
def role_permission_manager():
    return render_template('admin/admin_role_permission_manager.html',
                           id=current_user.id,
                           flask_env=ext.config.FLASK_ENV,
                           dict_role_permission=ext.permission_manager.get_dict())


@bp.route('/role_permission_manager/assign_role', methods=['GET', 'POST'])
@bp.route('/role_permission_manager/assign_role/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("assign_role")
def assign_role():
    if request.method == 'GET':
        return render_template('admin/admin_assign_role.html',
                               id=current_user.id,
                               dict_role_permission=ext.permission_manager.get_dict())

    account_id_raw = request.form.get("account_id")
    selected_role   = request.form.get("roles")

    if not account_id_raw or not account_id_raw.isdigit():
        flash("Please select a valid account ID.", "warning")
        return redirect(url_for("admin.role_permission_manager"))

    account_id = int(account_id_raw)

    account = ext.db_account_repository.get_by_id(account_id)
    if account is None:
        flash("ID doesn't exist", "warning")
        return redirect(url_for("admin.assign_role"))

    success, message, category = change_user_role(
        current_user_id=current_user.id,
        current_user_role_name=current_user.role_name,
        target_account=account,
        role_name=selected_role,
    )
    flash(message, category)
    return redirect(url_for("admin.admin_panel") if success else url_for("admin.assign_role"))


@bp.route('/role_permission_manager/create_role', methods=['GET', 'POST'])
@bp.route('/role_permission_manager/create_role/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("create_role")
def create_role():
    if request.method == 'GET':
        return render_template('admin/admin_create_role.html',
                               id=current_user.id,
                               dict_permissions=ext.permissions.DICT_PERMISSIONS_BY_TYPE)

    role_name             = str(request.form.get("role_name"))
    list_permissions_name = request.form.getlist("permissions")

    if not role_name:
        flash("Please enter role name.", "warning")
        return redirect(url_for("admin.create_role"))

    if ext.db_role_repository.role_exists(role_name):
        flash("This role already exists.", "error")
        return redirect(url_for("admin.create_role"))

    ext.permission_manager.create_role(role_name=role_name, list_permissions=list_permissions_name)
    flash("Role created successfully.", "success")
    return redirect(url_for("admin.role_permission_manager"))


@bp.route('/role_permission_manager/edit_role/<string:role_name>', methods=['GET', 'POST'])
@bp.route('/role_permission_manager/edit_role/<string:role_name>/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("edit_role")
def edit_role(role_name: str):
    if request.method == 'GET':
        if role_name in ext.permissions.LIST_DEFAULT_ROLES:
            flash("You cannot edit this role - It is a default role", "warning")
            return redirect(url_for("admin.role_permission_manager"))
        return render_template('admin/admin_edit_role.html',
                               id=current_user.id,
                               dict_permissions=ext.permissions.DICT_PERMISSIONS_BY_TYPE,
                               current_role_name=role_name)

    new_role_name         = str(request.form.get("role_name"))
    list_permissions_name = request.form.getlist("permissions")

    if not new_role_name:
        flash("Please enter role name.", "warning")
        return redirect(url_for("admin.create_role"))

    if ext.db_role_repository.role_exists(new_role_name):
        flash("This role already exists.", "error")
        return redirect(url_for("admin.create_role"))

    role_id = ext.db_role_repository.get_role_id(role_name=role_name)
    try:
        ext.permission_manager.edit_role(role_id=role_id,
                                         new_role_name=new_role_name,
                                         list_permissions=list_permissions_name)
        flash("Role edited successfully.", "success")
    except Exception:
        flash("An error has occurred", "error")
    finally:
        return redirect(url_for("admin.role_permission_manager"))


@bp.route('/role_permission_manager/delete_role/<string:role_name>', methods=['POST'])
@bp.route('/role_permission_manager/delete_role/<string:role_name>/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("delete_role")
def delete_role(role_name: str):
    if role_name in ext.permissions.LIST_DEFAULT_ROLES:
        flash(f"You cannot delete this role - It is a default role", "warning")
        return redirect(url_for("admin.role_permission_manager"))

    role_id = ext.db_role_repository.get_role_id(role_name=role_name)
    ext.permission_manager.delete_role(role_id=role_id)
    flash(f"Role '{role_name}' deleted successfully.", "success")
    return redirect(url_for("admin.role_permission_manager"))


# ── Gestion des utilisateurs ─────────────────────────────────────────────────

@bp.route('/users', methods=['GET'])
@bp.route('/users/', methods=['GET'])
@login_required
@require_permission("access_admin_panel")
@require_permission("view_users")
def users_list():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    search = request.args.get('q', '').strip() or None

    role_filter = request.args.get('role', type=int)
    if role_filter is not None and ext.db_role_repository.get_role_name(role_id=role_filter) is None:
        role_filter = None

    status_filter = request.args.get('status', '').strip().lower()
    if status_filter == 'active':
        is_active_filter = True
    elif status_filter == 'suspended':
        is_active_filter = False
    else:
        status_filter = ''
        is_active_filter = None

    pagination = ext.db_account_repository.get_all_paginated(
        page=page,
        per_page=ext.config.ADMIN_PAGE_SIZE,
        search=search,
        role_id=role_filter,
        is_active=is_active_filter,
    )

    filter_args = {}
    if search:
        filter_args['q'] = search
    if role_filter is not None:
        filter_args['role'] = role_filter
    if status_filter:
        filter_args['status'] = status_filter

    return render_template('admin/admin_users.html',
                           pagination=pagination,
                           users=pagination.get('items', []),
                           get_role_name=ext.db_role_repository.get_role_name,
                           roles=ext.db_role_repository.get_all_roles(),
                           search=search or '',
                           selected_role=role_filter,
                           selected_status=status_filter,
                           filter_args=filter_args)


@bp.route('/users/create', methods=['GET', 'POST'])
@bp.route('/users/create/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("create_user")
def user_create():
    if request.method == 'GET':
        return render_template('admin/admin_create_user.html',
                               roles=ext.db_role_repository.get_all_roles())

    success, message, category = create_user_account(
        current_user_role_name=current_user.role_name,
        email=request.form.get('email'),
        name=request.form.get('name'),
        raw_password=request.form.get('password'),
        role_name=request.form.get('role_name'),
    )
    flash(message, category)
    return redirect(url_for('admin.users_list') if success else url_for('admin.user_create'))


@bp.route('/users/<int:user_id>', methods=['GET'])
@bp.route('/users/<int:user_id>/', methods=['GET'])
@login_required
@require_permission("access_admin_panel")
@require_permission("view_users")
def user_detail(user_id: int):
    account = ext.db_account_repository.get_by_id(user_id)
    if account is None:
        flash("This user does not exist.", "warning")
        return redirect(url_for("admin.users_list"))

    role_name = ext.db_role_repository.get_role_name(role_id=account["role_id"])
    last_login = ext.db_account_repository.get_last_login_by_id(user_id)

    return render_template('admin/admin_user_detail.html',
                           account=account,
                           role_name=role_name,
                           last_login=last_login,
                           roles=ext.db_role_repository.get_all_roles())


@bp.route('/users/<int:user_id>/role', methods=['POST'])
@bp.route('/users/<int:user_id>/role/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("assign_role")
def user_update_role(user_id: int):
    account = ext.db_account_repository.get_by_id(user_id)
    if account is None:
        flash("This user does not exist.", "warning")
        return redirect(url_for("admin.users_list"))

    success, message, category = change_user_role(
        current_user_id=current_user.id,
        current_user_role_name=current_user.role_name,
        target_account=account,
        role_name=request.form.get("role_name"),
    )
    flash(message, category)
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route('/users/<int:user_id>/suspend', methods=['POST'])
@bp.route('/users/<int:user_id>/suspend/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("ban_user")
def user_suspend(user_id: int):
    account = ext.db_account_repository.get_by_id(user_id)
    if account is None:
        flash("This user does not exist.", "warning")
        return redirect(url_for("admin.users_list"))

    success, message, category = set_user_active_status(
        current_user_id=current_user.id,
        current_user_role_name=current_user.role_name,
        target_account=account,
        activate=False,
    )
    flash(message, category)
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route('/users/<int:user_id>/reactivate', methods=['POST'])
@bp.route('/users/<int:user_id>/reactivate/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("ban_user")
def user_reactivate(user_id: int):
    account = ext.db_account_repository.get_by_id(user_id)
    if account is None:
        flash("This user does not exist.", "warning")
        return redirect(url_for("admin.users_list"))

    success, message, category = set_user_active_status(
        current_user_id=current_user.id,
        current_user_role_name=current_user.role_name,
        target_account=account,
        activate=True,
    )
    flash(message, category)
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@bp.route('/users/<int:user_id>/delete/', methods=['POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("delete_user")
def user_delete(user_id: int):
    account = ext.db_account_repository.get_by_id(user_id)
    if account is None:
        flash("This user does not exist.", "warning")
        return redirect(url_for("admin.users_list"))

    success, message, category = delete_user_account(
        current_user_id=current_user.id,
        current_user_role_name=current_user.role_name,
        target_account=account,
    )
    flash(message, category)
    return redirect(url_for("admin.users_list") if success else url_for("admin.user_detail", user_id=user_id))
