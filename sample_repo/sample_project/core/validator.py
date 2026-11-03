"""Data validation helpers and schema verification."""
import re
from typing import Dict, Any, Optional

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def validate_email(email: str) -> bool:
    """Validate string matches basic email structure."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_payload(payload: Dict[str, Any]) -> bool:
    """Ensure required metadata keys exist in payload."""
    required_keys = {"id", "action", "user_email"}
    if not isinstance(payload, dict):
        return False
    if not required_keys.issubset(payload.keys()):
        return False
    return validate_email(payload["user_email"])

class ValidationError(Exception):
    """Raised when request payload fails schema validation."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field
