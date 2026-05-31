"""FastAPI dependencies for JWT authentication."""

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import decode_token

security = HTTPBearer()


class WebAuthRequired(Exception):
    """Raised by web route deps when teacher cookie is missing or invalid."""


async def require_teacher_web(request: Request) -> dict:
    """Validate access_token cookie for HTML web routes.

    Raises WebAuthRequired (→ redirect to /login) instead of 401.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise WebAuthRequired()
    try:
        payload = decode_token(token)
    except Exception:
        raise WebAuthRequired()
    if payload.get("role") != "teacher":
        raise WebAuthRequired()
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Decode the Bearer token and return the payload dict.

    Raises HTTP 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_student(payload: dict = Depends(get_current_user)) -> dict:
    """Require the caller to be a student. Raises 403 otherwise."""
    if payload.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return payload


async def require_teacher(payload: dict = Depends(get_current_user)) -> dict:
    """Require the caller to be a teacher. Raises 403 otherwise."""
    if payload.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return payload
