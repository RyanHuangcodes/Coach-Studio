from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Roster, Tier, User
from app.rate_limit import limiter
from app.schemas import UserCreate, UserLogin, UserOut
from app.security import (
    clear_session,
    create_session,
    get_current_user,
    hash_password,
    verify_password,
)
from app.config import settings
from app.tiers import DEFAULT_TIERS

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Precomputed at import time. When a login names an unknown email we still run
# one bcrypt verify against this hash so the request takes the same time as a
# real-user/wrong-password attempt — otherwise response latency would reveal
# which emails have accounts (user enumeration).
_DUMMY_PASSWORD_HASH = hash_password("timing-equalizer-not-a-real-password")


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def signup(payload: UserCreate, request: Request, response: Response, db: DbSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent signup for the same email won the race.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    db.refresh(user)

    for index, tier_name in enumerate(DEFAULT_TIERS):
        db.add(Tier(user_id=user.id, name=tier_name, sort_order=index))
    # Every coach starts with one team roster so the app always has a roster to
    # land on; they can rename it or add private-lesson rosters later.
    db.add(Roster(user_id=user.id, name="All Players", kind="team", sort_order=0))
    db.commit()

    create_session(db, response, user)
    return user


@router.post("/login", response_model=UserOut)
@limiter.limit("10/minute")
def login(payload: UserLogin, request: Request, response: Response, db: DbSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        # Run a throwaway verify so the unknown-email path costs the same bcrypt
        # time as a real one, then fail identically.
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    create_session(db, response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = request.cookies.get(settings.session_cookie_name)
    clear_session(db, response, token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
