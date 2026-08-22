import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import redis

class Config:
    """
    Application configuration.

    Production : secrets are read from Docker secrets
    Development : from environment variables (via .env)
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

    # Google Sign-In (OAuth 2.0 / OIDC) - Optional
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str | None = read_secret("google_client_secret") if ENV_PROD else os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_OAUTH_ENABLED: bool = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

    # Stripe - Optional
    STRIPE_SECRET_KEY: str | None = read_secret("stripe_secret_key") if ENV_PROD else os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = read_secret("stripe_webhook_secret") if ENV_PROD else os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PUBLISHABLE_KEY: str | None = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_ENABLED: bool = bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and STRIPE_PUBLISHABLE_KEY)

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

    UPLOAD_PRODUCT_IMAGE_FOLDER: Path = UPLOAD_FOLDER / "product_images"
    UPLOAD_PRODUCT_IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────── Uploads ───────────────────────────────── #

    MAX_CONTENT_LENGTH: int             = int(os.getenv("MAX_UPLOAD_SIZE_MB", "16")) * 1024 * 1024
    ALLOWED_EXTENSIONS_PROFILE_PICTURE: set[str] = {"png", "jpg", "jpeg"}
    ALLOWED_EXTENSIONS_PRODUCT_IMAGE: set[str]   = {"png", "jpg", "jpeg"}
    PRODUCT_IMAGE_MAX_SIZE: int         = 5 * 1024 * 1024

    # Whitelist of selectable icons for a product card (see
    # templates/shop/components/product_icons.html for the matching SVGs).
    # None/empty/unknown -> falls back to the default "box" icon.
    PRODUCT_ICON_CHOICES: list[str] = ["card", "pill", "heart", "shield", "cross"]

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

    # "Strict" would silently break Google Sign-In: the browser lands back on
    # /login/google/callback via a top-level cross-site navigation *from*
    # accounts.google.com, and Strict cookies are not sent on that request -
    # so Authlib can never find the state/nonce it stored before redirecting
    # to Google, and every callback fails with a mismatching_state error.
    # "Lax" still blocks cross-site POST/fetch (the actual CSRF vector);
    # state-changing requests are additionally covered by Flask-WTF's
    # CSRFProtect (see extensions.py), so this doesn't weaken CSRF defense.
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # Session lifetime
    SESSION_COOKIE_TIME_DAYS: int    = int(os.getenv("SESSION_COOKIE_TIME_DAYS", "0"))
    SESSION_COOKIE_TIME_HOURS: int   = int(os.getenv("SESSION_COOKIE_TIME_HOURS", "1"))
    SESSION_COOKIE_TIME_MINUTES: int = int(os.getenv("SESSION_COOKIE_TIME_MINUTES", "0"))

    # Drives the actual browser cookie's Max-Age (via session.permanent = True
    # in SessionManager.send_session()), kept in sync with the DB-tracked
    # `sessions.expires_at` above so both lifetimes agree.
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        days=SESSION_COOKIE_TIME_DAYS,
        hours=SESSION_COOKIE_TIME_HOURS,
        minutes=SESSION_COOKIE_TIME_MINUTES,
    )

    # 2FA code validity window
    TWOFA_TIMELAPS_MINUTES: int = int(os.getenv("TWOFA_TIMELAPS_MINUTES", "15"))

    # Admin-triggered password reset link validity window
    PASSWORD_RESET_TOKEN_TIMELAPS_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_TIMELAPS_MINUTES", "60"))

    # Email-change confirmation link validity window. The new address only
    # takes effect once this link is opened - proves the account owner
    # actually controls the mailbox they're switching to.
    EMAIL_CHANGE_TOKEN_TIMELAPS_MINUTES: int = int(os.getenv("EMAIL_CHANGE_TOKEN_TIMELAPS_MINUTES", "60"))

    # How long an unverified account (email_verified = 0) is allowed to sit
    # unclaimed before it's purged. Prevents "email squatting": someone
    # registering with an email they don't own, never finishing verification,
    # and permanently blocking the real owner from registering/using OAuth.
    UNVERIFIED_ACCOUNT_TTL_MINUTES: int = int(os.getenv("UNVERIFIED_ACCOUNT_TTL_MINUTES", "30"))

    # Minimum length enforced server-side on registration and password change
    # (client-side/HTML validation alone is trivially bypassed with a direct POST).
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "10"))

    # Version of the Terms & Conditions / Privacy Policy shown at registration.
    # Bump this whenever the legal text changes so stored consents stay tied
    # to the version the user actually accepted.
    TERMS_VERSION: str = os.getenv("TERMS_VERSION", "1.0")

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

    # ───────────────────────────── Shop ──────────────────────────────────── #
    # The catalog lives in the `products` table (Data/schema/products.py) and
    # is managed from the admin panel - prices are never trusted from the
    # client, every Checkout Session amount is built server-side from a fresh
    # DB read. SHOP_CURRENCY is fixed across the whole catalog because Stripe
    # Checkout only supports a single currency per session: every product is
    # created in this currency (see blueprints/shop/service.py::ProductService).
    SHOP_CURRENCY: str = os.getenv("SHOP_CURRENCY", os.getenv("NFC_CARD_CURRENCY", "eur"))

    # Seed values for the original MediLink NFC card product - used only once,
    # by ProductsSeeder, to create its row on first boot. After that its price
    # lives in the database and is editable from the admin panel.
    NFC_CARD_SKU: str            = "medilink-nfc-card"
    NFC_CARD_NAME: str           = "MediLink NFC Card"
    NFC_CARD_DESCRIPTION: str    = "A durable NFC card that first responders can tap to instantly access your emergency medical information."
    NFC_CARD_PRICE_CENTS: int    = int(os.getenv("NFC_CARD_PRICE_CENTS", "2999"))

    # Countries Stripe Checkout is allowed to collect a shipping address for.
    # France-only for launch - widen this list later without any data migration.
    STRIPE_SHIPPING_ALLOWED_COUNTRIES: list[str] = ["FR"]

    # ──────────────────────────── Proxy Trust ───────────────────────────── #

    ALLOWED_HOSTS: set[str] = {
        "medilink.ltjs.net",
        "localhost",
        "127.0.0.1",
        "[::1]",
    }

    PROXY_TRUSTED_HOP_COUNT: int = int(os.getenv("PROXY_TRUSTED_HOP_COUNT", "2"))
    EXTERNAL_URL_BASE: str = os.getenv("EXTERNAL_URL_BASE", "https://medilink.ltjs.net")