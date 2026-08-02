import logging
import extensions as ext
from models.user import User

logger = logging.getLogger(__name__)


def register_login_manager():

    @ext.login_manager.user_loader
    def load_user(user_id):
        try:
            user_id_int = int(user_id)
            user = User(user_id_int)
            logger.debug("User %s loaded successfully",user_id_int)
            return user

        except (ValueError, TypeError) as e:
            logger.warning("Invalid user ID format: %s", str(e))
            return None

        except Exception as e:
            logger.error("Error loading user %s: %s", user_id, str(e))
            return None