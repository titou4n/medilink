import extensions as ext
import datetime

class TwofaManager():
    def __init__(self):
        self.db_twofa = ext.db_twofa_repository
        self.db_account = ext.db_account_repository
        self.email_manager = ext.email_manager
        self.hash_manager = ext.hash_manager
        self.config = ext.config

    def generate_code(self) -> str:
        """Génère un code 2FA de 6 chiffres cryptographiquement sûr."""
        return self.hash_manager.generate_numeric_otp(digits=6)

    def send_code(self, user_id:int) -> None:
        random_code = self.generate_code()
        self.email_manager.send_two_factor_authentication_code_with_html(user_id, random_code)
        self.db_twofa.insert(
            user_id=user_id,
            code_hash=self.hash_manager.generate_password_hash(random_code),
            created_at=ext.utils.get_datetime_isoformat())

    def verif_need_to_sent_new_code(self, user_id:int) -> bool:
        code_hash = self.db_twofa.get_latest_valid(user_id=user_id)
        if code_hash is None:
            #raise TwoFactorCodeNotFoundError("No 2FA code found for this user.")
            return True
        
        if code_hash["used"]:
            #raise TwoFactorCodeAlreadyUsedError("This 2FA code has already been used.")
            return True
        
        if code_hash["attempts"] >= 3:
            #raise TwoFactorTooManyAttemptsError("Too many invalid attempts.")
            return True
        
        created_at = datetime.datetime.fromisoformat(code_hash["created_at"])
        if ext.utils.datetime_is_expired_minutes(created_at, self.config.TWOFA_TIMELAPS_MINUTES):
            #raise TwoFactorCodeExpiredError("The 2FA code has expired.")
            return True
        
        return False

    def verif_code(self, code:str, user_id:int) -> bool:

        code_hash = self.db_twofa.get_latest_valid(user_id=user_id)
        if code_hash is None:
            self.db_twofa.delete_by_user_id(user_id=user_id)
            raise TwoFactorCodeNotFoundError("No 2FA code found for this user.")
        
        if code_hash["used"]:
            self.db_twofa.delete_by_user_id(user_id=user_id)
            raise TwoFactorCodeAlreadyUsedError("This 2FA code has already been used.")
        
        if code_hash["attempts"] >= 3:
            self.db_twofa.delete_by_user_id(user_id=user_id)
            raise TwoFactorTooManyAttemptsError("Too many invalid attempts.")
        
        created_at = datetime.datetime.fromisoformat(code_hash["created_at"])
        if ext.utils.datetime_is_expired_minutes(created_at, self.config.TWOFA_TIMELAPS_MINUTES):
            self.db_twofa.delete_by_user_id(user_id=user_id)
            raise TwoFactorCodeExpiredError("The 2FA code has expired.")
        
        if not self.hash_manager.check_password(code, code_hash["code_hash"]):
            self.db_twofa.increment_attempts(id_two_factor_codes=code_hash["id_two_factor_codes"])
            raise TwoFactorInvalidCodeError("Invalid 2FA code.")
        
        self.db_twofa.mark_as_used(id_two_factor_codes=code_hash["id_two_factor_codes"])
        self.db_twofa.delete_by_user_id(user_id=user_id)
        self.db_account.update_email_verified(user_id, True)
        return True
    
    def delete_old_code_hash(self, user_id):
        self.db_twofa.delete_by_user_id(user_id=user_id)


class TwoFactorAuthError(Exception):
    """Base exception for 2FA errors."""
    pass

class TwoFactorCodeNotFoundError(TwoFactorAuthError):
    pass

class TwoFactorCodeAlreadyUsedError(TwoFactorAuthError):
    pass

class TwoFactorTooManyAttemptsError(TwoFactorAuthError):
    pass

class TwoFactorCodeExpiredError(TwoFactorAuthError):
    pass

class TwoFactorInvalidCodeError(TwoFactorAuthError):
    pass