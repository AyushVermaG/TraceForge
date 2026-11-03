"""Authentication and security token validator."""
import hashlib
import time
from typing import Optional, Dict
from sample_project.core.validator import validate_email

class AuthService:
    """Handles credentials hashing, session tokens, and security audits."""

    def __init__(self, secret_salt: str = "traceforge_demo_secret"):
        self.salt = secret_salt
        self.active_sessions: Dict[str, float] = {}

    def generate_token(self, user_email: str) -> Optional[str]:
        """Validate email and mint deterministic SHA-256 session token."""
        if not validate_email(user_email):
            return None
        
        timestamp = str(time.time())
        token_input = f"{user_email}:{self.salt}:{timestamp}".encode("utf-8")
        token = hashlib.sha256(token_input).hexdigest()
        self.active_sessions[token] = time.time()
        return token

    def verify_token(self, token: str) -> bool:
        """Check token existence and expiration."""
        if token not in self.active_sessions:
            return False
        issued_at = self.active_sessions[token]
        # Valid for 3600 seconds
        return (time.time() - issued_at) < 3600
