"""
Data/repositories/emergency_information_repository.py
----------------------------------------------------
CRUD operations for the ``emergency_information`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class EmergencyInformationRepository:
    """Repository for emergency information records."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_id(self, record_id: int) -> Optional[sqlite3.Row]:
        """Return an emergency information record by its ID."""

        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM emergency_information
                WHERE id = ?;
                """,
                (record_id,),
            ).fetchone()

    def get_by_user_id(self, user_id: int) -> Optional[sqlite3.Row]:
        """Return emergency information linked to a user."""

        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM emergency_information
                WHERE user_id = ?;
                """,
                (user_id,),
            ).fetchone()

    def get_by_public_token(
        self,
        public_token: str
    ) -> Optional[sqlite3.Row]:
        """Return an active emergency record by its public token."""

        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM emergency_information
                WHERE public_token = ?
                  AND is_active = 1;
                """,
                (public_token,),
            ).fetchone()

    def get_all(self) -> list[sqlite3.Row]:
        """Return every emergency information record."""

        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM emergency_information
                ORDER BY updated_at DESC;
                """
            ).fetchall()

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        """Return paginated emergency information records."""

        with self._db.connect() as conn:
            total = conn.execute(
                """
                SELECT COUNT(*)
                FROM emergency_information;
                """
            ).fetchone()[0]

            offset = (page - 1) * per_page
            items = conn.execute(
                """
                SELECT *,
                       first_name || ' ' || last_name as full_name
                FROM emergency_information
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?;
                """,
                (per_page, offset),
            ).fetchall()

            pages = (total + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < pages

            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "prev_num": page - 1 if has_prev else None,
                "next_num": page + 1 if has_next else None,
            }

    def token_exists(
        self,
        public_token: str
    ) -> bool:
        """Check whether a public token already exists."""

        with self._db.connect() as conn:
            result = conn.execute(
                """
                SELECT 1
                FROM emergency_information
                WHERE public_token = ?;
                """,
                (public_token,),
            ).fetchone()

            return result is not None

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def create(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        date_of_birth: Optional[str],
        gender: Optional[str],
        blood_type: Optional[str],
        height_cm: Optional[int],
        weight_kg: Optional[float],
        allergies: Optional[str],
        medical_conditions: Optional[str],
        current_medications: Optional[str],
        critical_info: Optional[str],
        medical_notes: Optional[str],
        emergency_contact_name: Optional[str],
        emergency_contact_phone: Optional[str],
        emergency_contact_relation: Optional[str],
        doctor_name: Optional[str],
        doctor_phone: Optional[str],
        organ_donor: bool,
        public_token: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """Create a new emergency information record."""

        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO emergency_information (
                    user_id,
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    blood_type,
                    height_cm,
                    weight_kg,
                    allergies,
                    medical_conditions,
                    current_medications,
                    critical_info,
                    medical_notes,
                    emergency_contact_name,
                    emergency_contact_phone,
                    emergency_contact_relation,
                    doctor_name,
                    doctor_phone,
                    organ_donor,
                    public_token,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
                """,
                (
                    user_id,
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    blood_type,
                    height_cm,
                    weight_kg,
                    allergies,
                    medical_conditions,
                    current_medications,
                    critical_info,
                    medical_notes,
                    emergency_contact_name,
                    emergency_contact_phone,
                    emergency_contact_relation,
                    doctor_name,
                    doctor_phone,
                    int(organ_donor),
                    public_token,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def update_last_public_access(
        self,
        record_id: int,
        last_public_access: str
    ) -> None:
        """Update the last public access timestamp."""

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE emergency_information
                SET last_public_access = ?
                WHERE id = ?;
                """,
                (last_public_access, record_id),
            )
            conn.commit()

    def update_all_fields(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        date_of_birth: Optional[str],
        gender: Optional[str],
        blood_type: Optional[str],
        height_cm: Optional[int],
        weight_kg: Optional[float],
        allergies: Optional[str],
        medical_conditions: Optional[str],
        current_medications: Optional[str],
        critical_info: Optional[str],
        medical_notes: Optional[str],
        emergency_contact_name: Optional[str],
        emergency_contact_phone: Optional[str],
        emergency_contact_relation: Optional[str],
        doctor_name: Optional[str],
        doctor_phone: Optional[str],
        organ_donor: bool,
        updated_at: str,
    ) -> None:
        """Update every editable field of a user's emergency information record."""

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE emergency_information
                SET
                    first_name = ?,
                    last_name = ?,
                    date_of_birth = ?,
                    gender = ?,
                    blood_type = ?,
                    height_cm = ?,
                    weight_kg = ?,
                    allergies = ?,
                    medical_conditions = ?,
                    current_medications = ?,
                    critical_info = ?,
                    medical_notes = ?,
                    emergency_contact_name = ?,
                    emergency_contact_phone = ?,
                    emergency_contact_relation = ?,
                    doctor_name = ?,
                    doctor_phone = ?,
                    organ_donor = ?,
                    updated_at = ?
                WHERE user_id = ?;
                """,
                (
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    blood_type,
                    height_cm,
                    weight_kg,
                    allergies,
                    medical_conditions,
                    current_medications,
                    critical_info,
                    medical_notes,
                    emergency_contact_name,
                    emergency_contact_phone,
                    emergency_contact_relation,
                    doctor_name,
                    doctor_phone,
                    int(organ_donor),
                    updated_at,
                    user_id,
                ),
            )
            conn.commit()

    def update_public_token(
        self,
        record_id: int,
        public_token: str,
    ) -> None:
        """Update the public token of a record."""

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE emergency_information
                SET public_token = ?
                WHERE id = ?;
                """,
                (public_token, record_id),
            )
            conn.commit()

    def set_active(
        self,
        record_id: int,
        active: bool,
        updated_at: str,
    ) -> None:
        """Enable or disable a public emergency record."""

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE emergency_information
                SET is_active = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    int(active),
                    updated_at,
                    record_id,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(
        self,
        record_id: int
    ) -> None:
        """Delete an emergency information record."""

        with self._db.connect() as conn:
            conn.execute(
                """
                DELETE FROM emergency_information
                WHERE id = ?;
                """,
                (record_id,),
            )
            conn.commit()