from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(payload: dict, expires_delta: timedelta) -> str:
    """Encode a JWT with the given payload and expiry."""
    data = payload.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    data["exp"] = expire
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.

    Raises:
        jwt.ExpiredSignatureError: if the token has expired.
        jwt.InvalidTokenError: if the token is invalid for any other reason.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
