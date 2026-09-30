"""Web Push: store browser subscriptions and send notifications.

Push is optional — if VAPID keys aren't configured, everything here no-ops and
the rest of the app is unaffected.
"""
import json
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.models import PushSubscription, User
from app.schemas import PushSubscribeRequest, PushUnsubscribeRequest, VapidKeyOut
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/push", tags=["push"])


def push_to_user(db: DbSession, user_id: str, title: str, body: str, url: str = "/") -> None:
    """Best-effort push to every subscription a user has. Never raises — a push
    failure must not break the message send. Prunes expired subscriptions."""
    if not user_id or not settings.vapid_private_key:
        return
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    if not subs:
        return
    try:
        from pywebpush import webpush, WebPushException
        from py_vapid import Vapid01
    except Exception:  # library not installed
        return
    vapid = Vapid01.from_raw(settings.vapid_private_key.encode())
    payload = json.dumps({"title": title, "body": body, "url": url})
    pruned = False
    for sub in subs:
        info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        try:
            webpush(
                subscription_info=info,
                data=payload,
                vapid_private_key=vapid,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=600,
                timeout=5,
            )
        except WebPushException as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (404, 410):
                db.delete(sub)
                pruned = True
            else:
                logger.warning("web push failed: %s", exc)
        except Exception as exc:  # network/timeout — ignore
            logger.warning("web push error: %s", exc)
    if pruned:
        db.commit()


@router.get("/key", response_model=VapidKeyOut)
def get_public_key(current_user: User = Depends(get_current_user)):
    return VapidKeyOut(public_key=settings.vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(
    payload: PushSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    existing = (
        db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    )
    if existing is not None:
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
    else:
        db.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=payload.endpoint,
                p256dh=payload.keys.p256dh,
                auth=payload.keys.auth,
            )
        )
    db.commit()


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    payload: PushUnsubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint, PushSubscription.user_id == current_user.id
    ).delete()
    db.commit()
