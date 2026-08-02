# blueprints/settings/services.py
# Logique métier settings : upload photo de profil, export des données.

import os
import logging
import mimetypes
import secrets
from io import BytesIO
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

import extensions as ext

logger = logging.getLogger(__name__)


def build_data_export(user_id: int) -> BytesIO:
    """Construit le fichier texte d'export des données personnelles."""
    content  = "=== PERSONALE DATA EXPORT ===\n"
    content += f"Date       : {ext.utils.format_datetime(ext.utils.get_datetime_isoformat())}\n"
    content += f"ID         : {user_id}\n"
    content += f"Username   : {ext.db_account_repository.get_username_by_id(user_id)}\n"
    content += f"Name       : {ext.db_account_repository.get_name_by_id(user_id)}\n"
    content += f"Pay        : {ext.db_account_repository.get_pay_by_id(user_id)} TC\n\n"

    metadata  = ext.db_account_repository.get_metadata_by_user_id(user_id)
    content  += "=== MÉTADONNÉES ===\n\n"
    for meta in metadata:
        content += f"{ext.utils.format_datetime(meta['date_connected'])} - IP: {meta['ipv4']}\n"

    return BytesIO(content.encode('utf-8'))


def validate_profile_picture(file) -> tuple[bool, str]:
    """Valide un fichier image de profil."""

    if not file or file.filename == '':
        return False, "No file provided"

    # 1. Vérifier le nom de fichier
    filename = secure_filename(file.filename)
    if not filename or '.' not in filename:
        return False, "Invalid filename"

    # 2. Vérifier l'extension
    allowed_extensions = current_app.config.get("ALLOWED_EXTENSIONS_PROFILE_PICTURE", {'png', 'jpg', 'jpeg'})
    ext_name = filename.rsplit('.', 1)[1].lower()
    if ext_name not in allowed_extensions:
        return False, f"File extension not allowed: {ext_name}"

    # 3. Vérifier le type MIME
    file.seek(0)
    mime_type = file.mimetype or mimetypes.guess_type(filename)[0]
    allowed_mimes = {'image/png', 'image/jpeg'}
    if mime_type not in allowed_mimes:
        return False, f"Invalid MIME type: {mime_type}"

    # 4. Vérifier les magic bytes (BMP non listé : déjà exclu par ALLOWED_EXTENSIONS_PROFILE_PICTURE)
    file.seek(0)
    header = file.read(8)
    if not (
        (header[:4] == b'\x89PNG') or  # PNG
        (header[:2] == b'\xff\xd8')    # JPEG
    ):
        return False, "Invalid image file (magic bytes)"

    # 5. Vérifier que c'est une image valide
    file.seek(0)
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except Exception as e:
        return False, f"Corrupted image file: {str(e)}"

    # 6. Vérifier la taille
    file.seek(0, 2)  # Aller à la fin
    file_size = file.tell()
    max_size = current_app.config.get("PROFILE_PICTURE_MAX_SIZE", 5 * 1024 * 1024)
    if file_size > max_size:
        return False, f"File too large: {file_size} bytes (max: {max_size})"

    file.seek(0)
    return True, ""


def save_profile_picture(user_id: int, file) -> bool:
    """Sauvegarde la photo de profil avec validation complète."""

    # Valider le fichier
    is_valid, error_msg = validate_profile_picture(file)
    if not is_valid:
        logger.warning("Invalid profile picture upload attempt for user %s: %s", user_id, error_msg)
        return False

    # Générer un nom sûr
    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    new_filename = f"user_{user_id}_{secrets.token_hex(8)}.{extension}"

    folder = current_app.config['UPLOAD_PROFILE_PICTURE_FOLDER']
    filepath = os.path.join(folder, new_filename)

    # Ré-encoder l'image (pixels uniquement) plutôt que de sauvegarder le fichier
    # tel quel : neutralise toute donnée additionnelle (polyglotte, métadonnées)
    # au-delà de ce que PIL décode réellement comme image.
    # img.verify() (dans validate_profile_picture) invalide l'objet PIL pour tout
    # usage ultérieur - on rouvre donc le fichier depuis le début.
    try:
        file.seek(0)
        img = Image.open(file)
        if extension in ("jpg", "jpeg"):
            img = img.convert("RGB")
            save_format = "JPEG"
        else:  # png
            img = img.convert("RGBA")
            save_format = "PNG"
        img.save(filepath, format=save_format)
    except Exception as e:
        logger.warning("Failed to re-encode profile picture for user %s: %s", user_id, str(e))
        return False

    # Supprimer l'ancienne image si elle existe
    old_path = ext.db_account_repository.get_profile_picture_path(user_id)
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except Exception as e:
            logger.warning("Failed to delete old profile picture for user %s: %s", user_id, str(e))

    ext.db_account_repository.update_profile_picture_path(user_id, filepath)

    logger.info("Profile picture uploaded for user %s", user_id)
    return True
