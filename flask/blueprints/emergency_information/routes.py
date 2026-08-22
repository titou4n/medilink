"""
Routes for the Emergency Information module.

URL map:
  GET  /emergency_information/                       → user dashboard
  GET  /emergency_information/edit                    → edit form
  POST /emergency_information/edit                    → save form
  POST /emergency_information/token/regenerate         → regenerate public token
  POST /emergency_information/delete                  → delete record
  GET  /emergency_information/qr.png                  → download the QR code as PNG
  GET  /emergency_information/qr.svg                  → download the QR code as SVG
  GET  /emergency_information/qr/print                 → printable QR page
  GET  /emergency_information/public/<token>           → public emergency page (no auth)
  GET  /emergency_information/admin/                   → admin dashboard
  POST /emergency_information/admin/<id>/toggle        → admin enable/disable
  POST /emergency_information/admin/<id>/delete        → admin delete
"""
import io
import logging
from flask import render_template, redirect, request, flash, url_for, abort, send_file
from flask_login import login_required, current_user
from blueprints.emergency_information import bp
from blueprints.emergency_information.permissions import (
    can_edit_record, can_regenerate_token, can_delete_record
)
from blueprints.emergency_information.utils.qr_generator import (
    generate_qr_png, generate_qr_svg, generate_qr_data_uri,
)
import extensions as ext
from utils.decorators import require_permission, require_admin
from utils.url_helper import get_safe_base_url, build_external_url

logger = logging.getLogger(__name__)


def _get_public_url(record) -> str:
    """Build the existing public emergency URL for a record (token-based)."""
    return build_external_url(url_for('emergency_information.public_view', token=record.public_token))


@bp.route('/')
@bp.route('')
@login_required
@require_permission("emergency_information_access")
def dashboard():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        base_url = get_safe_base_url()
        return render_template(
            'emergency_information/dashboard.html',
            id=current_user.id,
            record=record,
            base_url=base_url,
        )
    except Exception as e:
        logger.error("Error loading dashboard for user %s: %s", current_user.id, str(e))
        flash('An error occurred while loading your information.', 'error')
        return redirect(url_for('main.home'))


@bp.route('/edit', methods=['GET', 'POST'])
@bp.route('/edit/', methods=['GET', 'POST'])
@login_required
@require_permission("emergency_information_access")
def edit():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)

        if record and not can_edit_record(record):
            abort(403)

        if request.method == 'GET':
            return render_template(
                'emergency_information/edit.html',
                id=current_user.id,
                record=record,
                blood_types=ext.config.BLOOD_TYPES,
                gender_options=ext.config.GENDER_OPTIONS,
                relation_options=ext.config.RELATION_OPTIONS,
            )

        record, errors = ext.emergency_information_service.create_or_update_record(
            user_id=current_user.id,
            form_data=request.form,
        )

        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('emergency_information.edit'))

        flash('Your medical information has been saved successfully.', 'success')
        logger.info("Medical information saved for user %s", current_user.id)
        return redirect(url_for('emergency_information.dashboard'))
    except Exception as e:
        logger.error("Error saving medical information for user %s: %s", current_user.id, str(e))
        flash('An error occurred while saving your information.', 'error')
        return redirect(url_for('emergency_information.edit'))


@bp.route('/token/regenerate', methods=['POST'])
@bp.route('/token/regenerate/', methods=['POST'])
@login_required
@require_permission("emergency_information_access")
def regenerate_token():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        if not record:
            abort(404)
        if not can_regenerate_token(record):
            abort(403)

        ext.emergency_information_service.regenerate_token_for_record(record)
        flash('Your public emergency link has been regenerated. The previous link is now invalid.', 'success')
        logger.info("Token regenerated for user %s", current_user.id)
        return redirect(url_for('emergency_information.dashboard'))
    except Exception as e:
        logger.error("Error regenerating token for user %s: %s", current_user.id, str(e))
        flash('An error occurred while regenerating your link.', 'error')
        return redirect(url_for('emergency_information.dashboard'))


@bp.route('/qr.png')
@login_required
@require_permission("emergency_information_access")
def qr_png():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        if not record:
            abort(404)

        png_bytes = generate_qr_png(_get_public_url(record))
        return send_file(
            io.BytesIO(png_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name='medilink-emergency-qr.png',
        )
    except Exception as e:
        logger.error("Error generating QR PNG for user %s: %s", current_user.id, str(e))
        flash('An error occurred while generating your QR code.', 'error')
        return redirect(url_for('emergency_information.dashboard'))


@bp.route('/qr.svg')
@login_required
@require_permission("emergency_information_access")
def qr_svg():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        if not record:
            abort(404)

        svg_bytes = generate_qr_svg(_get_public_url(record))
        return send_file(
            io.BytesIO(svg_bytes),
            mimetype='image/svg+xml',
            as_attachment=True,
            download_name='medilink-emergency-qr.svg',
        )
    except Exception as e:
        logger.error("Error generating QR SVG for user %s: %s", current_user.id, str(e))
        flash('An error occurred while generating your QR code.', 'error')
        return redirect(url_for('emergency_information.dashboard'))


@bp.route('/qr/print')
@bp.route('/qr/print/')
@login_required
@require_permission("emergency_information_access")
def qr_print():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        if not record:
            abort(404)

        public_url = _get_public_url(record)
        return render_template(
            'emergency_information/qr_print.html',
            record=record,
            public_url=public_url,
            qr_data_uri=generate_qr_data_uri(public_url),
        )
    except Exception as e:
        logger.error("Error rendering QR print page for user %s: %s", current_user.id, str(e))
        flash('An error occurred while preparing your printable QR code.', 'error')
        return redirect(url_for('emergency_information.dashboard'))


@bp.route('/delete', methods=['POST'])
@bp.route('/delete/', methods=['POST'])
@login_required
@require_permission("emergency_information_access")
def delete():
    try:
        record = ext.emergency_information_service.get_record_for_user(current_user.id)
        if not record:
            abort(404)
        if not can_delete_record(record):
            abort(403)

        ext.emergency_information_service.delete_record(record)
        flash('Your emergency medical information has been deleted.', 'success')
        logger.info("Emergency information deleted for user %s", current_user.id)
        return redirect(url_for('emergency_information.dashboard'))
    except Exception as e:
        logger.error("Error deleting emergency information for user %s: %s", current_user.id, str(e))
        flash('An error occurred while deleting your information.', 'error')
        return redirect(url_for('emergency_information.dashboard'))


@bp.route('/public/<string:token>')
@bp.route('/public/<string:token>/')
@ext.limiter.limit(f"{ext.config.PUBLIC_RATE_LIMIT} per minute")
def public_view(token: str):
    """
    Publicly accessible page — no authentication required.
    Intended for emergency responders scanning a QR code or receiving a link.
    """
    try:
        if not token or not token.strip():
            abort(404)

        record = ext.emergency_information_service.get_public_record(token)
        if not record:
            abort(404)

        return render_template(
            'emergency_information/public_view.html',
            record=record,
        )
    except Exception as e:
        logger.error("Error loading public emergency view for token: %s", str(e))
        abort(404)


@bp.route('/admin/')
@bp.route('/admin')
@login_required
@require_admin
def admin_dashboard():
    try:
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        pagination = ext.emergency_information_service.get_all_paginated(
            page=page,
            per_page=ext.config.ADMIN_PAGE_SIZE
        )

        if not pagination or 'items' not in pagination:
            pagination = {'items': [], 'total': 0, 'pages': 0, 'current': page}

        return render_template(
            'emergency_information/admin_dashboard.html',
            pagination=pagination,
            records=pagination.get('items', []),
        )
    except Exception as e:
        logger.error("Error loading admin dashboard: %s", str(e))
        flash('An error occurred while loading records.', 'error')
        return render_template(
            'emergency_information/admin_dashboard.html',
            pagination={'items': [], 'total': 0, 'pages': 0, 'current': 1},
            records=[],
        )


@bp.route('/admin/<int:record_id>/toggle', methods=['POST'])
@bp.route('/admin/<int:record_id>/toggle/', methods=['POST'])
@login_required
@require_admin
def admin_toggle(record_id: int):
    try:
        record = ext.emergency_information_service.get_by_id(record_id)
        if not record:
            abort(404)

        # Security: Verify admin ownership/access
        record_user_id = getattr(record, 'user_id', None)
        if not record_user_id:
            logger.error("Record %s has no user_id", record_id)
            abort(400)

        is_active = getattr(record, 'is_active', False)
        ext.emergency_information_service.set_record_active(record, not is_active)

        state = 'enabled' if not is_active else 'disabled'
        flash(f'Emergency profile {state} successfully.', 'success')
        logger.info("Admin %s toggled emergency profile %s", current_user.id, record_id)
        return redirect(url_for('emergency_information.admin_dashboard'))
    except Exception as e:
        logger.error("Error toggling record %s by admin %s: %s", record_id, current_user.id, str(e))
        flash('An error occurred while updating the profile.', 'error')
        return redirect(url_for('emergency_information.admin_dashboard'))


@bp.route('/admin/<int:record_id>/delete', methods=['POST'])
@bp.route('/admin/<int:record_id>/delete/', methods=['POST'])
@login_required
@require_admin
def admin_delete(record_id: int):
    try:
        record = ext.emergency_information_service.get_by_id(record_id)
        if not record:
            abort(404)

        # Security: Verify admin ownership/access
        record_user_id = getattr(record, 'user_id', None)
        if not record_user_id:
            logger.error("Record %s has no user_id", record_id)
            abort(400)

        ext.emergency_information_service.delete_record(record)
        flash('Emergency profile deleted.', 'success')
        logger.info("Admin %s deleted emergency profile %s", current_user.id, record_id)
        return redirect(url_for('emergency_information.admin_dashboard'))
    except Exception as e:
        logger.error("Error deleting record %s by admin %s: %s", record_id, current_user.id, str(e))
        flash('An error occurred while deleting the profile.', 'error')
        return redirect(url_for('emergency_information.admin_dashboard'))


@bp.route('/admin/<int:record_id>/view')
@bp.route('/admin/<int:record_id>/view/')
@login_required
@require_admin
def admin_view(record_id: int):
    try:
        record = ext.emergency_information_service.get_by_id(record_id)
        if not record:
            abort(404)

        return render_template(
            'emergency_information/public_view.html',
            record=record,
            admin_mode=True,
        )
    except Exception as e:
        logger.error("Error viewing record %s: %s", record_id, str(e))
        flash('An error occurred while loading the profile.', 'error')
        return redirect(url_for('emergency_information.admin_dashboard'))
