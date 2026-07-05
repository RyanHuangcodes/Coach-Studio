import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.models import Session as SessionModel
from app.models import User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_session(db: DbSession, response: Response, user: User) -> None:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(SessionModel(id=token, user_id=user.id, expires_at=expires_at))
    db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_hours * 3600,
    )


def clear_session(db: DbSession, response: Response, token: Optional[str]) -> None:
    if token:
        db.query(SessionModel).filter(SessionModel.id == token).delete()
        db.commit()
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def get_current_user(request: Request, db: DbSession = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    now = datetime.now(timezone.utc)
    session = db.query(SessionModel).filter(SessionModel.id == token).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if session.expires_at < now:
        # Opportunistic cleanup: purge this and any other expired sessions so
        # the table doesn't grow without bound.
        db.query(SessionModel).filter(SessionModel.expires_at < now).delete()
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return user
