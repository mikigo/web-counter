"""Authentication: bcrypt password hashing and session management."""

import secrets
import time
from typing import Dict, Optional

import bcrypt

# In-memory session store: token -> {"username": str, "created_at": float}
_sessions: Dict[str, dict] = {}

SESSION_MAX_AGE = 86400  # 24 hours


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session(username: str) -> str:
    """Create a new session token for the given username."""
    token = secrets.token_hex(32)
    _sessions[token] = {"username": username, "created_at": time.time()}
    return token


def validate_session(token: str) -> Optional[str]:
    """Validate a session token. Returns username if valid, None otherwise."""
    if token not in _sessions:
        return None
    session = _sessions[token]
    if time.time() - session["created_at"] > SESSION_MAX_AGE:
        del _sessions[token]
        return None
    return session["username"]


def destroy_session(token: str):
    """Destroy a session token."""
    _sessions.pop(token, None)
