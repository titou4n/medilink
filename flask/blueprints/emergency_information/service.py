"""
Services/emergency_information_service.py
-----------------------------------------
Business logic for the Emergency Information module.
Handles validation, repository calls and token generation.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from models.emergency_information import EmergencyInformation
from Data.repositories.emergency_information_repository import (
    EmergencyInformationRepository,
)

from blueprints.emergency_information.utils.token_generator import (
    generate_public_token,
)

from blueprints.emergency_information.utils.validators import (
    compute_age,
    validate_boolean,
    validate_blood_type,
    validate_date_of_birth,
    validate_gender,
    validate_height,
    validate_long_text,
    validate_phone,
    validate_short_text,
    validate_weight,
)

import extensions as ext

logger = logging.getLogger(__name__)


class EmergencyInformationService:
    """Service layer for emergency information records."""

    def __init__(
        self,
        repository: EmergencyInformationRepository
    ) -> None:
        self._repository = repository

    # ------------------------------------------------------------------ #
    # Conversion helpers
    # ------------------------------------------------------------------ #

    def _row_to_model(self, row: sqlite3.Row) -> EmergencyInformation:
        """Convert a database row to an EmergencyInformation model."""
        return EmergencyInformation(
            id=row["id"],
            user_id=row["user_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            age=compute_age(row["date_of_birth"]),
            date_of_birth=row["date_of_birth"],
            gender=row["gender"],
            blood_type=row["blood_type"],
            height_cm=row["height_cm"],
            weight_kg=row["weight_kg"],
            allergies=row["allergies"],
            medical_conditions=row["medical_conditions"],
            current_medications=row["current_medications"],
            critical_info=row["critical_info"],
            medical_notes=row["medical_notes"],
            emergency_contact_name=row["emergency_contact_name"],
            emergency_contact_phone=row["emergency_contact_phone"],
            emergency_contact_relation=row["emergency_contact_relation"],
            doctor_name=row["doctor_name"],
            doctor_phone=row["doctor_phone"],
            organ_donor=bool(row["organ_donor"]),
            public_token=row["public_token"],
            is_active=bool(row["is_active"]),
            last_public_access=row["last_public_access"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ------------------------------------------------------------------ #
    # Token helpers
    # ------------------------------------------------------------------ #

    def _generate_unique_token(self) -> str:
        """Generate a unique public token."""

        for _ in range(10):
            token = generate_public_token()

            if not self._repository.token_exists(token):
                return token

        raise RuntimeError(
            "Unable to generate a unique public token."
        )

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_id(self, record_id: int) -> Optional[EmergencyInformation]:
        """Return a record by its ID."""
        row = self._repository.get_by_id(record_id)
        return self._row_to_model(row) if row else None

    def get_by_user_id(self, user_id: int) -> Optional[EmergencyInformation]:
        """Return a record linked to a user."""
        row = self._repository.get_by_user_id(user_id)
        return self._row_to_model(row) if row else None

    def get_public_record(
        self,
        public_token: str
    ) -> Optional[EmergencyInformation]:
        """
        Return an active public record and update
        its last access timestamp.
        """

        row = self._repository.get_by_public_token(
            public_token
        )

        if row:
            self._repository.update_last_public_access(
                row["id"],
                datetime.utcnow().isoformat()
            )
            return self._row_to_model(row)

        return None

    def get_record_for_user(self, user_id: int) -> Optional[EmergencyInformation]:
        return self.get_by_user_id(user_id)

    def create_or_update_record(self, user_id: int, form_data: dict) -> tuple[Optional[EmergencyInformation], list[str]]:
        return self.create_or_update(user_id, form_data)

    def regenerate_token_for_record(
        self,
        record: EmergencyInformation
    ) -> str:
        """Regenerate a public token for a record."""
        return self.regenerate_token(record.id)

    def delete_record(
        self,
        record: EmergencyInformation
    ) -> None:
        """Delete a record."""
        self.delete(record.id)

    def set_record_active(
        self,
        record: EmergencyInformation,
        active: bool
    ) -> None:
        """Enable or disable a record."""
        self.set_active(record.id, active)

    def get_all(self) -> list[EmergencyInformation]:
        """Return all emergency information records."""
        rows = self._repository.get_all()
        return [self._row_to_model(row) for row in rows]

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        """Return paginated emergency information records."""
        result = self._repository.get_all_paginated(page, per_page)
        result["items"] = [self._row_to_model(row) for row in result["items"]]
        return result

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _parse_form_data(self, form_data: dict) -> tuple[dict, list[str]]:
        """
        Validate and sanitize form data.
        Returns cleaned data and validation errors.
        """

        errors: list[str] = []
        cleaned: dict = {}

        def _check(key:str, value, error: Optional[str]) -> None:
            if error:
                errors.append(error)
            else:
                cleaned[key] = value

        # -------------------------------------------------------------- #
        # Identity
        # -------------------------------------------------------------- #

        val, err = validate_short_text(form_data.get("first_name"), "First name")
        _check("first_name", val, err)

        val, err = validate_short_text(form_data.get("last_name"), "Last name")
        _check("last_name", val, err)

        val, err = validate_date_of_birth(form_data.get("date_of_birth"))
        _check("date_of_birth", val, err)

        val, err = validate_gender(form_data.get("gender"), ext.config.GENDER_OPTIONS)
        _check("gender", val, err)

        val, err = validate_blood_type(form_data.get("blood_type"))
        _check("blood_type", val, err)

        # -------------------------------------------------------------- #
        # Physical
        # -------------------------------------------------------------- #

        val, err = validate_height(form_data.get("height_cm"))
        _check("height_cm", val, err)

        val, err = validate_weight(form_data.get("weight_kg"))
        _check("weight_kg", val, err)

        # -------------------------------------------------------------- #
        # Medical
        # -------------------------------------------------------------- #

        for key, label in [
            ("allergies", "Allergies"),
            ("medical_conditions", "Medical conditions"),
            ("current_medications", "Current medications"),
            ("critical_info", "Critical information"),
            ("medical_notes", "Medical notes"),
        ]:
            val, err = validate_long_text(
                form_data.get(key),
                label
            )

            _check(key, val, err)

        # -------------------------------------------------------------- #
        # Emergency contact
        # -------------------------------------------------------------- #

        val, err = validate_short_text(
            form_data.get("emergency_contact_name"),
            "Emergency contact name"
        )
        _check("emergency_contact_name", val, err)

        val, err = validate_phone(
            form_data.get("emergency_contact_phone")
        )
        _check("emergency_contact_phone", val, err)

        val, err = validate_short_text(
            form_data.get("emergency_contact_relation"),
            "Emergency contact relation"
        )
        _check("emergency_contact_relation", val, err)

        # -------------------------------------------------------------- #
        # Doctor
        # -------------------------------------------------------------- #

        val, err = validate_short_text(
            form_data.get("doctor_name"),
            "Doctor name"
        )
        _check("doctor_name", val, err)

        val, err = validate_phone(
            form_data.get("doctor_phone")
        )
        _check("doctor_phone", val, err)

        # -------------------------------------------------------------- #
        # Organ donor
        # -------------------------------------------------------------- #

        cleaned["organ_donor"] = validate_boolean(
            form_data.get("organ_donor", False)
        )

        return cleaned, errors

    # ------------------------------------------------------------------ #
    # Create / Update
    # ------------------------------------------------------------------ #

    def create_or_update(self, user_id: int, form_data: dict) -> tuple[Optional[EmergencyInformation], list[str]]:
        """
        Create or update a user's emergency information.
        """

        cleaned, errors = self._parse_form_data(form_data)

        if errors:
            return None, errors

        now = ext.utils.get_datetime_isoformat()
        record = self._repository.get_by_user_id(user_id)

        # -------------------------------------------------------------- #
        # Update existing
        # -------------------------------------------------------------- #

        if record:
            logger.info("Updating emergency information "
                        "for user_id=%s",user_id)

            self._repository.update_all_fields(
                user_id=user_id,
                first_name=cleaned["first_name"],
                last_name=cleaned["last_name"],
                date_of_birth=cleaned["date_of_birth"],
                gender=cleaned["gender"],
                blood_type=cleaned["blood_type"],
                height_cm=cleaned["height_cm"],
                weight_kg=cleaned["weight_kg"],
                allergies=cleaned["allergies"],
                medical_conditions=cleaned["medical_conditions"],
                current_medications=cleaned["current_medications"],
                critical_info=cleaned["critical_info"],
                medical_notes=cleaned["medical_notes"],
                emergency_contact_name=cleaned["emergency_contact_name"],
                emergency_contact_phone=cleaned["emergency_contact_phone"],
                emergency_contact_relation=cleaned["emergency_contact_relation"],
                doctor_name=cleaned["doctor_name"],
                doctor_phone=cleaned["doctor_phone"],
                organ_donor=cleaned["organ_donor"],
                updated_at=now,
            )

            updated_row = self._repository.get_by_user_id(user_id)
            return (
                self._row_to_model(updated_row) if updated_row else None,
                []
            )

        # -------------------------------------------------------------- #
        # Create new
        # -------------------------------------------------------------- #

        logger.info(
            "Creating emergency information "
            "for user_id=%s",
            user_id
        )

        public_token = self._generate_unique_token()

        self._repository.create(
            user_id=user_id,
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            date_of_birth=cleaned["date_of_birth"],
            gender=cleaned["gender"],
            blood_type=cleaned["blood_type"],
            height_cm=cleaned["height_cm"],
            weight_kg=cleaned["weight_kg"],
            allergies=cleaned["allergies"],
            medical_conditions=cleaned["medical_conditions"],
            current_medications=cleaned["current_medications"],
            critical_info=cleaned["critical_info"],
            medical_notes=cleaned["medical_notes"],
            emergency_contact_name=cleaned["emergency_contact_name"],
            emergency_contact_phone=cleaned["emergency_contact_phone"],
            emergency_contact_relation=cleaned["emergency_contact_relation"],
            doctor_name=cleaned["doctor_name"],
            doctor_phone=cleaned["doctor_phone"],
            organ_donor=cleaned["organ_donor"],
            public_token=public_token,
            created_at=now,
            updated_at=now,
        )

        created_row = self._repository.get_by_user_id(user_id)
        return (
            self._row_to_model(created_row) if created_row else None,
            []
        )

    # ------------------------------------------------------------------ #
    # Public access
    # ------------------------------------------------------------------ #

    def regenerate_token(
        self,
        record_id: int
    ) -> str:
        """Regenerate a public token."""

        token = self._generate_unique_token()

        self._repository.update_public_token(record_id, token)

        return token

    def set_active(
        self,
        record_id: int,
        active: bool
    ) -> None:
        """Enable or disable public access."""

        self._repository.set_active(
            record_id,
            active,
            datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(
        self,
        record_id: int
    ) -> None:
        """Delete an emergency information record."""

        self._repository.delete(record_id)