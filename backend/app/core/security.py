import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,  # unique per token: guarantees distinct tokens even within the
        # same second, and gives a hook for a future server-side revocation denylist.
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


class InvalidTokenError(Exception):
    pass


def decode_token_payload(token: str, expected_type: Literal["access", "refresh"]) -> dict:
    """Returns the full decoded payload (sub, type, iat, exp, jti) if valid, else raises
    InvalidTokenError. Use this when the caller needs more than just the subject -- e.g. logout
    needs `jti`/`exp` to record a revocation entry."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise InvalidTokenError("Could not validate token")

    if payload.get("type") != expected_type:
        raise InvalidTokenError("Wrong token type")
    if not payload.get("sub"):
        raise InvalidTokenError("Missing subject")
    if not payload.get("jti"):
        raise InvalidTokenError("Missing jti")
    return payload


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> str:
    """Returns the user id (sub) if valid, else raises InvalidTokenError."""
    return decode_token_payload(token, expected_type)["sub"]
