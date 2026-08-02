# blueprints/admin/routes.py
# Préfixe : /admin_panel  (défini dans create_app)

from flask import render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user

from blueprints.admin import bp
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

    if not ext.db_account_repository.exists_by_id(user_id=account_id):
        flash("ID doesn't exist", "warning")
        return redirect(url_for("admin.assign_role"))

    if not selected_role:
        flash("Please select a role.", "warning")
        return redirect(url_for("admin.assign_role"))

    if current_user.id == account_id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.assign_role"))

    account = ext.db_account_repository.get_by_id(account_id)
    super_admin_role_id = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_SUPER_ADMIN)
    admin_role_id       = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_ADMIN)

    if account["role_id"] == super_admin_role_id:
        flash("You cannot change the role of a Super Admin.", "warning")
        return redirect(url_for("admin.assign_role"))

    if account["role_id"] == admin_role_id:
        flash("You cannot change the role of an Admin.", "warning")
        return redirect(url_for("admin.assign_role"))

    role_id = ext.db_role_repository.get_role_id(role_name=selected_role)
    if role_id is None:
        flash("Role doesn't exist", "warning")
        return redirect(url_for("admin.assign_role"))

    # Security: only a Super Admin may grant the Super Admin or Admin role.
    # Without this check, any account holding just "access_admin_panel" +
    # "assign_role" (e.g. a custom role) could grant itself/others full admin rights.
    if role_id in (super_admin_role_id, admin_role_id) and current_user.role_name != ext.config.ROLE_NAME_SUPER_ADMIN:
        flash("Only a Super Admin can assign the Admin or Super Admin role.", "danger")
        return redirect(url_for("admin.assign_role"))

    ext.db_account_repository.update_role(user_id=account_id, role_id=role_id)
    flash("Role assigned successfully.", "success")
    return redirect(url_for("admin.admin_panel"))


@bp.route('/role_permission_manager/create_role', methods=['GET', 'POST'])
@bp.route('/role_permission_manager/create_role/', methods=['GET', 'POST'])
@login_required
@require_permission("access_admin_panel")
@require_permission("create_role")
def create_role():
    if request.method == 'GET':
        return render_template('admin/admin_create_role.html',
                               id=current_user.id,
                               dict_permissions=ext.config.DICT_PERMISSIONS_BY_TYPE)

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
        if role_name in ext.config.LIST_DEFAULT_ROLES:
            flash("You cannot edit this role - It is a default role", "warning")
            return redirect(url_for("admin.role_permission_manager"))
        return render_template('admin/admin_edit_role.html',
                               id=current_user.id,
                               dict_permissions=ext.config.DICT_PERMISSIONS_BY_TYPE,
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
    if role_name in ext.config.LIST_DEFAULT_ROLES:
        flash(f"You cannot delete this role - It is a default role", "warning")
        return redirect(url_for("admin.role_permission_manager"))

    role_id = ext.db_role_repository.get_role_id(role_name=role_name)
    ext.permission_manager.delete_role(role_id=role_id)
    flash(f"Role '{role_name}' deleted successfully.", "success")
    return redirect(url_for("admin.role_permission_manager"))
