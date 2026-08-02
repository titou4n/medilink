"""
Data/models/emergency_information.py
------------------------------------
Model representing emergency medical information records.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class EmergencyInformation:
    """
    Represents critical medical information for a user.
    Accessible publicly through a secure token for emergency responders.
    """

    # ------------------------------------------------------------------ #
    # Primary fields
    # ------------------------------------------------------------------ #

    id: Optional[int]

    # ------------------------------------------------------------------ #
    # Identity
    # ------------------------------------------------------------------ #

    user_id: int
    first_name: str
    last_name: str
    age: Optional[int]
    date_of_birth: Optional[str]
    gender: Optional[str]
    blood_type: Optional[str]

    # ------------------------------------------------------------------ #
    # Physical
    # ------------------------------------------------------------------ #

    height_cm: Optional[int]
    weight_kg: Optional[float]

    # ------------------------------------------------------------------ #
    # Medical
    # ------------------------------------------------------------------ #

    allergies: Optional[str]
    medical_conditions: Optional[str]
    current_medications: Optional[str]
    critical_info: Optional[str]
    medical_notes: Optional[str]

    # ------------------------------------------------------------------ #
    # Emergency contact
    # ------------------------------------------------------------------ #

    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_relation: Optional[str]

    # ------------------------------------------------------------------ #
    # Healthcare provider
    # ------------------------------------------------------------------ #

    doctor_name: Optional[str]
    doctor_phone: Optional[str]

    # ------------------------------------------------------------------ #
    # Organ donor
    # ------------------------------------------------------------------ #

    organ_donor: bool = False

    # ------------------------------------------------------------------ #
    # Public access
    # ------------------------------------------------------------------ #

    public_token: str = ""
    is_active: bool = True
    last_public_access: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #

    created_at: str = ""
    updated_at: str = ""

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""

        token_preview = (
            f"{self.public_token[:8]}..."
            if self.public_token
            else "None"
        )

        return (
            f"<EmergencyInformation "
            f"id={self.id} "
            f"user_id={self.user_id} "
            f"token={token_preview}>"
        )