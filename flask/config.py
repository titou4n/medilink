import os
from pathlib import Path
from dotenv import load_dotenv
import redis

class Config:
    """
    Application configuration.

    Secrets are read from Docker secrets in production and from
    environment variables (via .env) in development.
    """

    load_dotenv()

    # ─────────────────────────── Environment ────────────────────────────── #

    ENV_PROD: bool = os.getenv("ENV_PROD", "false").lower() == "true"

    FLASK_ENV: str = "production" if ENV_PROD else "development"
    DEBUG: bool = not ENV_PROD
    
    #_______________________KEY_________________________#

    @staticmethod
    def read_secret(name):
        try:
            with open(f"/run/secrets/{name}") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    SECRET_KEY = read_secret("secret_key") if ENV_PROD else os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is missing")
    
    EMAIL_SUPER_ADMIN: str = os.getenv("EMAIL_SUPER_ADMIN", "titouservice.mail@gmail.com")
    SUPER_ADMIN_INITIAL_PASSWORD_LENGTH: int = 24
    ROLE_NAME_SUPER_ADMIN: str = "super_admin"
    NAME_SUPER_ADMIN: str = "SUPER ADMIN"

    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "titouservice.mail@gmail.com")
    EMAIL_APP_PASSWORD = read_secret("email_app_password") if ENV_PROD else os.getenv("EMAIL_APP_PASSWORD")
    if not EMAIL_APP_PASSWORD:
        raise RuntimeError("EMAIL_APP_PASSWORD is missing")

    # ──────────────────────────── Paths ─────────────────────────────────── #

    BASE_DIR: Path = Path(__file__).parent.resolve()
    DATA_DIR: Path = BASE_DIR / "Data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    DATABASE_FOLDER: Path = DATA_DIR / "db"
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)
    DATABASE_URL: str             = str(DATABASE_FOLDER / "database.db")

    UPLOAD_FOLDER: Path = BASE_DIR / "static" / "uploads"
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    UPLOAD_PROFILE_PICTURE_FOLDER: Path = UPLOAD_FOLDER / "profile_pictures"
    UPLOAD_PROFILE_PICTURE_FOLDER.mkdir(parents=True, exist_ok=True)

    PATH_DEFAULT_PROFILE_PICTURE: Path = BASE_DIR / "static" / "img" / "profile-default.png"

    # ──────────────────────────── Uploads ───────────────────────────────── #

    MAX_CONTENT_LENGTH: int             = int(os.getenv("MAX_UPLOAD_SIZE_MB", "16")) * 1024 * 1024
    ALLOWED_EXTENSIONS_PROFILE_PICTURE: set[str] = {"png", "jpg", "jpeg"}

    # ──────────────────────── Flask-Session ─────────────────────────────── #

    SESSION_TYPE: str = "redis"
    REDIS_URL: str = os.getenv("RATELIMIT_STORAGE_URI", "redis://localhost:6379/0")
    SESSION_REDIS = redis.from_url(REDIS_URL)
    SESSION_PERMANENT: bool      = False
    SESSION_USE_SIGNER: bool     = True

    SESSION_COOKIE_NAME: str     = "session_id"
    SESSION_COOKIE_DOMAIN        = None
    SESSION_COOKIE_PATH          = None
    SESSION_COOKIE_HTTPONLY: bool = True          # Blocks JS access to the cookie
    SESSION_COOKIE_SECURE: bool  = ENV_PROD       # Requires HTTPS in production
    SESSION_COOKIE_SAMESITE: str = "Strict"

    SESSION_COOKIE_MAX_AGE: int = 3600  # 1 heure

    # Session lifetime
    SESSION_COOKIE_TIME_DAYS: int    = int(os.getenv("SESSION_COOKIE_TIME_DAYS", "0"))
    SESSION_COOKIE_TIME_HOURS: int   = int(os.getenv("SESSION_COOKIE_TIME_HOURS", "1"))
    SESSION_COOKIE_TIME_MINUTES: int = int(os.getenv("SESSION_COOKIE_TIME_MINUTES", "0"))

    # 2FA code validity window
    TWOFA_TIMELAPS_MINUTES: int = int(os.getenv("TWOFA_TIMELAPS_MINUTES", "15"))

    # Password generation
    PASSWORD_GENERATION_LENGTH: int = 20

    # Minimum length enforced server-side on registration and password change
    # (client-side/HTML validation alone is trivially bypassed with a direct POST).
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "10"))

    # ─────────────────────── Database reset flags ───────────────────────── #

    NEED_TO_RESET_DB_EXCEPT_ACCOUNT: bool        = os.getenv("NEED_TO_RESET_DB_EXCEPT_ACCOUNT", "false").lower() == "true"
    NEED_TO_RESET_ALL_DB: bool                   = os.getenv("NEED_TO_RESET_ALL_DB", "false").lower() == "true"
    NEED_TO_RESET_ROLES_PERMISSIONS_TABLES: bool = os.getenv("NEED_TO_RESET_ROLES_PERMISSIONS_TABLES", "false").lower() == "true"
    CREATE_SEEDED_ACCOUNTS: bool = os.getenv("CREATE_SEEDED_ACCOUNTS", "false").lower() == "true"

    # ──────────────────────── Built-in accounts ─────────────────────────── #

    ROLE_NAME_SUPER_ADMIN: str = "super_admin"
    ROLE_NAME_ADMIN: str = "admin"

    # Debug user (development only)
    EMAIL_DEBUG: str       = os.getenv("EMAIL_DEBUG", "titouservice.mail@gmail.com")
    PASSWORD_DEBUG: str    = os.getenv("PASSWORD_DEBUG", "password_debug")
    ROLE_NAME_DEBUG: str   = ROLE_NAME_SUPER_ADMIN
    NAME_DEBUG : str       = "DEBUG"

    # ────────────────────── Emergency information ───────────────────────── #
    TOKEN_LENGTH          = 48              # bytes -> secrets.token_hex(48) = 96 hex chars
    ADMIN_PAGE_SIZE       = int(os.getenv("EMERGENCY_INFO_ADMIN_PAGE_SIZE", "25"))
    BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'Unknown']
    GENDER_OPTIONS = [
        ('male',            'Male'),
        ('female',          'Female'),
        ('other',           'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    RELATION_OPTIONS = [
        'Spouse', 'Partner', 'Parent', 'Child', 'Sibling',
        'Friend', 'Colleague', 'Neighbor', 'Other',
    ]

    MAX_TEXT_FIELD: int     = 5000
    MAX_SHORT_FIELD: int    = 150
    MAX_PHONE_FIELD: int    = 30
    PUBLIC_RATE_LIMIT: int = 50

    # ──────────────────────────── Proxy Trust ───────────────────────────── #

    ALLOWED_HOSTS: set[str] = {
        "medilink.ltjs.net",
        "localhost",
        "127.0.0.1",
        "[::1]",
    }

    PROXY_TRUSTED_HOP_COUNT: int = int(os.getenv("PROXY_TRUSTED_HOP_COUNT", "2"))
    EXTERNAL_URL_BASE: str = os.getenv("EXTERNAL_URL_BASE", "https://medilink.ltjs.net")