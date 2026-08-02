"""
Data/schema/emergency_information.py
-----------------------------------
DDL for ``emergency_information`` table.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_EMERGENCY_INFORMATION: str = """
CREATE TABLE IF NOT EXISTS emergency_information (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                      INTEGER NOT NULL UNIQUE,

    first_name                   TEXT,
    last_name                    TEXT,
    date_of_birth                TEXT,
    gender                       TEXT,
    blood_type                   TEXT,

    height_cm                    INTEGER,
    weight_kg                    REAL,

    allergies                    TEXT,
    medical_conditions           TEXT,
    current_medications          TEXT,

    critical_info                TEXT,
    medical_notes                TEXT,

    emergency_contact_name       TEXT,
    emergency_contact_phone      TEXT,
    emergency_contact_relation   TEXT,

    doctor_name                  TEXT,
    doctor_phone                 TEXT,

    organ_donor                  INTEGER NOT NULL DEFAULT 1,

    public_token                 TEXT    NOT NULL UNIQUE,
    is_active                    INTEGER NOT NULL DEFAULT 1,

    last_public_access           TEXT,

    created_at                   TEXT    NOT NULL,
    updated_at                   TEXT    NOT NULL,

    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_EMERGENCY_INFORMATION_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_emergency_information_user_id
    ON emergency_information(user_id);
"""

INDEX_EMERGENCY_INFORMATION_PUBLIC_TOKEN: str = """
CREATE INDEX IF NOT EXISTS idx_emergency_information_public_token
    ON emergency_information(public_token);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_EMERGENCY_INFORMATION,
    INDEX_EMERGENCY_INFORMATION_USER_ID,
    INDEX_EMERGENCY_INFORMATION_PUBLIC_TOKEN,
]