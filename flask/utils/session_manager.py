import logging
from datetime import datetime, timedelta
from flask import request, session as flask_session
from requests.exceptions import RequestException, Timeout
import secrets
import hashlib
import requests
import extensions as ext

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.db_session = ext.db_session_repository
        self.config = ext.config
        self._request_session = None

    def init_app(self, app_instance):
        self._request_session = requests.Session()

    def get_client_ip(self) -> str | None:
        """
        Get the client's real IP.

        Delegates to extensions.get_client_identifier(), whose value already
        comes from ProxyFix (installed in app.py) resolving request.remote_addr
        at the WSGI layer. Do not re-implement header parsing here - a second,
        unverified reading of CF-Connecting-IP/X-Forwarded-For/X-Real-IP would
        reintroduce IP spoofing on session-hijack detection even though
        rate-limiting stays protected (see audits/).
        """
        return ext.get_client_identifier()

    def get_ip_session(self) -> str | None:
        try:
            session_id = flask_session.get("session_id")
            if not session_id:
                return None

            client_ip = self.get_client_ip()
            if not client_ip:
                return None

            session_id_hash = self.hash_session_id(session_id)

            db_session = self.db_session.get_by_hash(session_id_hash=session_id_hash)

            if not db_session:
                return None

            db_session = dict(db_session)

            if db_session.get("is_revoked", False):
                return None

            expires_at_str = db_session.get("expires_at")
            if not expires_at_str:
                return None

            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                logger.warning(
                    "Invalid expires_at format for session %s",
                    session_id_hash
                )
                self.revoke_session(session_id_hash)
                return None

            if expires_at < ext.utils.get_datetime_utc():
                self.revoke_session(session_id_hash)
                return None

            ip_hash_stored = db_session.get("ip_hash")
            if not ip_hash_stored:
                return None

            if ip_hash_stored != self.hash_ip(client_ip):
                logger.warning("Session hijacking attempt detected for session %s", session_id_hash)
                self.revoke_session(session_id_hash)
                return None

            return client_ip

        except Exception:
            logger.exception("Error in get_ip_session")
            return None

    def get_ip_location(self, ip_address: str) -> str | None:
        """Récupère la localisation d'une IP."""
        
        if not ip_address:
            return None
        
        try:
            # Validation de l'IP
            import ipaddress
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                logger.warning("Invalid IP address: %s", ip_address)
                return None
            
            # Timeout court (5 secondes)
            response = requests.get(
                f"https://ipapi.co/{ip_address}/json/",
                timeout=5,
                verify=True,  # Vérifier le certificat SSL
            )
            
            # Vérifier le statut
            if response.status_code != 200:
                logger.warning("IP location API returned status %s", response.status_code)
                return None
            
            # Valider la réponse
            data = response.json()
            if not isinstance(data, dict) or 'city' not in data:
                logger.warning("Invalid IP location response")
                return None
            
            location = f"{data.get('city', '')}, {data.get('country_code', '')}"
            return location.strip() if location.strip() else None
            
        except Timeout:
            logger.warning("IP location API timeout for: %s", ip_address)
            return None
        except RequestException as e:
            logger.error("IP location API error: %s", str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error getting IP location: %s", str(e))
            return None
    
    def get_location(self) -> str | None:
        ip = self.get_ip_session()
        if not ip:
            return None
        return self.get_ip_location(ip_address=ip)

    ############################################
    #_______________SESSION____________________#
    ############################################

    def generate_session_id(self) -> str:
        return secrets.token_urlsafe(32)
    
    def hash_session_id(self, session_id) -> str:
        return hashlib.sha256(session_id.encode()).hexdigest()
    
    def hash_ip(self, ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()
    
    def hash_user_agent(self, user_agent: str) -> str:
        return hashlib.sha256(user_agent.encode()).hexdigest()

    def verif_session_is_active(self, session_id_hash: str) -> bool:
        try:
            db_session = self.db_session.get_by_hash(session_id_hash=session_id_hash)

            if not db_session:
                return False

            if db_session.get("is_revoked", False):
                return False

            expires_at_str = db_session.get("expires_at")
            if not expires_at_str:
                return False

            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at < ext.utils.get_datetime_utc():
                self.revoke_session(session_id_hash)
                return False

            ip_hash_stored = db_session.get("ip_hash")
            current_ip = self.get_client_ip() or ""
            if ip_hash_stored != self.hash_ip(current_ip):
                self.revoke_session(session_id_hash)
                return False

            ua_hash_stored = db_session.get("user_agent_hash")
            current_ua = request.headers.get("User-Agent", "")
            if ua_hash_stored != self.hash_user_agent(current_ua):
                self.revoke_session(session_id_hash)
                return False

            self.db_session.touch(
                session_id_hash=session_id_hash,
                last_used_at=ext.utils.get_datetime_utc()
            )
            return True
        except Exception as e:
            logger.error("Error verifying session: %s", str(e))
            return False

    def send_session(self, user_id:int) -> None:
        session_id = self.generate_session_id()
        session_id_hash = self.hash_session_id(session_id)

        ip_hash = self.hash_ip(self.get_client_ip() or "")
        ua_hash = self.hash_user_agent(request.headers.get("User-Agent", ""))
        now = ext.utils.get_datetime_utc()

        self.db_session.insert(
            session_id_hash=session_id_hash,
            user_id=user_id,
            ip_hash=ip_hash,
            user_agent_hash=ua_hash,
            created_at=now,
            expires_at=now + timedelta(days=self.config.SESSION_COOKIE_TIME_DAYS,
                                    hours=self.config.SESSION_COOKIE_TIME_HOURS,
                                    minutes=self.config.SESSION_COOKIE_TIME_MINUTES),
            is_revoked=0)

        flask_session["session_id"] = session_id

    def revoke_session(self, session_id_hash:str) -> None:
        self.db_session.revoke(session_id_hash=session_id_hash)
        return None

    def get_session_info(self, session_id_hash:str):
        return self.db_session.get_by_hash(session_id_hash=session_id_hash)

    def get_current_session_id_hash(self) -> str | None:
        try:
            session_id = flask_session.get("session_id")
            if not session_id:
                return None

            session_id_hash = self.hash_session_id(session_id=session_id)
            if not self.verif_session_is_active(session_id_hash=session_id_hash):
                return None

            return session_id_hash
        except Exception as e:
            logger.error("Error getting current session hash: %s", str(e))
            return None
    
    def get_current_user_id(self) -> int | None:
        try:
            session_id = flask_session.get("session_id")
            if not session_id:
                return None

            session_id_hash = self.hash_session_id(session_id=session_id)
            if not self.verif_session_is_active(session_id_hash=session_id_hash):
                return None

            db_session = self.db_session.get_by_hash(session_id_hash=session_id_hash)
            if not db_session:
                return None

            user_id = db_session.get("user_id")
            return int(user_id) if user_id is not None else None
        except (ValueError, TypeError) as e:
            logger.error("Error retrieving current user ID: %s", str(e))
            return None
    
    def logout(self) -> None:
        try:
            session_id = flask_session.get("session_id")
            if not session_id:
                return

            session_id_hash = self.hash_session_id(session_id=session_id)
            db_session = self.db_session.get_by_hash(session_id_hash=session_id_hash)

            if db_session:
                self.revoke_session(session_id_hash)

            flask_session.clear()
            logger.info("User logged out successfully")
        except Exception as e:
            logger.error("Error during logout: %s", str(e))
            flask_session.clear()

    def logout_user_from_all_devices(self, user_id: int) -> None:
        try:
            self.db_session.revoke_all_for_user(user_id=user_id)
            flask_session.clear()
            logger.info("User %s logged out from all devices", user_id)
        except Exception as e:
            logger.error("Error logging out user from all devices: %s", str(e))

    def logout_session_owned(self, session_id_hash: str, user_id: int) -> bool:
        """Revoke a session, but only if it belongs to *user_id*. Returns True on success."""
        return self.db_session.revoke_owned(session_id_hash=session_id_hash, user_id=user_id)

    def delete_session_owned(self, session_id_hash: str, user_id: int) -> bool:
        """Delete a session, but only if it belongs to *user_id*. Returns True on success."""
        return self.db_session.delete_owned(session_id_hash=session_id_hash, user_id=user_id)

    def send_temp_2fa_session(self, user_id: int) -> None:
        flask_session["temp_user_id"] = user_id

    def finalize_2fa_session(self, user_id: int) -> None:
        flask_session.pop("temp_user_id", None)
        self.send_session(user_id=user_id)