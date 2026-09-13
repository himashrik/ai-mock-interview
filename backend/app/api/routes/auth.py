from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import bearer_scheme, get_current_user
from app.core.limiter import limiter
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_token_payload,
    hash_password,
    verify_password,
)
from app.db.base import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest, UserOut
from app.services import token_denylist

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    # httpOnly: never readable by JS (mitigates XSS token theft).
    # SameSite=Lax: sent on top-level navigation/same-site requests, blocked on most cross-site
    # requests (mitigates CSRF) while still working for a frontend on a different port in dev.
    # Path scoped to /auth so the cookie isn't sent on every single API request.
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path="/auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), full_name=payload.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=AccessTokenResponse)
@limiter.limit("10/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Same generic message for "no such user" and "wrong password" — don't leak which.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    _set_refresh_cookie(response, create_refresh_token(str(user.id)))
    return AccessTokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided.")

    try:
        user_id = decode_token(refresh_token, expected_type="refresh")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Rotate the refresh token on every use (mitigates replay of a stolen-but-old cookie value).
    _set_refresh_cookie(response, create_refresh_token(str(user.id)))
    return AccessTokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    # Clear the refresh cookie so no new access token can be minted from it, AND revoke the
    # current access token immediately (rather than letting it remain valid until its natural
    # <=15 min expiry) by recording its jti in the denylist.
    _clear_refresh_cookie(response)

    if credentials is not None:
        try:
            payload = decode_token_payload(credentials.credentials, expected_type="access")
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            token_denylist.revoke(db, jti=payload["jti"], expires_at=expires_at)
        except InvalidTokenError:
            pass  # already-invalid token needs no revocation

    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
