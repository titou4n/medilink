# extensions.py

import logging
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

from Data.database_manager import DatabaseManager
from Data.connection import DatabaseConnection

from Data.seeders.roles_permissions import RolesPermissionsSeeder
from Data.seeders.accounts_seeder   import AccountsSeeder

from Data.repositories.account_repository           import AccountRepository
from Data.repositories.role_repository              import RoleRepository
from Data.repositories.session_repository           import SessionRepository
from Data.repositories.twofa_repository             import TwoFARepository
from Data.repositories.emergency_information_repository import EmergencyInformationRepository

from config import Config
from utils.utils import Utils
from utils.session_manager import SessionManager
from utils.permissions_manager import PermissionsManager
from utils.email_manager import EmailManager
from utils.hash_manager import HashManager
from utils.twofa_manager import TwofaManager
from utils.decorators import *

from permissions import Permissions

def get_client_identifier():
    """
    Real client IP for rate-limiting.

    Trust resolution does NOT happen here: ProxyFix(x_for=PROXY_TRUSTED_HOP_COUNT)
    is installed on the WSGI stack in app.py and already rewrites
    request.remote_addr, at the WSGI layer, by peeling exactly
    PROXY_TRUSTED_HOP_COUNT trusted hops (cloudflared + nginx) off
    X-Forwarded-For before any Flask code runs — including this function. So
    by the time we get here, request.remote_addr already IS the real visitor
    IP; there's no header left to read or peer address left to verify.

    Do not add CF-Connecting-IP / X-Forwarded-For parsing back into this
    function: request.remote_addr at this point is never Cloudflare's own
    address (ProxyFix already consumed that hop), so any such check would be
    dead code that never fires — see audits/ for the history of that mistake.
    """
    return get_remote_address()

# Config
config = Config()
permissions = Permissions()

# Flask Extensions
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_client_identifier,
    storage_uri=config.REDIS_URL,
    strategy="fixed-window",
    headers_enabled=True,
    default_limits=[]
)

# Shared connection factory ─ one per process
db_connection = DatabaseConnection(db_path=config.DATABASE_URL)

# Initialise the schema + seeders
_db_manager = DatabaseManager(db_connection)

# ------------------------------------------------------------------ #
# Repository singletons
# ------------------------------------------------------------------ #

db_account_repository: AccountRepository = AccountRepository(db_connection)
db_role_repository: RoleRepository = RoleRepository(db_connection)
db_session_repository: SessionRepository = SessionRepository(db_connection)
db_twofa_repository: TwoFARepository = TwoFARepository(db_connection)
db_emergency_information_repository: EmergencyInformationRepository = EmergencyInformationRepository(db_connection)

# ------------------------------------------------------------------ #
# Service singletons
# ------------------------------------------------------------------ #

from blueprints.emergency_information.service import EmergencyInformationService

emergency_information_service: EmergencyInformationService = EmergencyInformationService(db_emergency_information_repository)

# Manager
session_manager = SessionManager()
permission_manager = PermissionsManager()
email_manager = EmailManager()
hash_manager = HashManager()
twofa_manager = TwofaManager()

# Utils/Tools
utils = Utils()

# Initialise seeders
_roles_permissions_seeders = RolesPermissionsSeeder()
_accounts_seeder = AccountsSeeder(
    config=config,
    account_repo=db_account_repository,
    role_repo=db_role_repository,
    hash_manager=hash_manager,
)
