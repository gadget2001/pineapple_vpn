import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import send_admin_log
from app.core.security import create_access_token, verify_telegram_init_data
from app.db.session import get_db
from app.models.referral import Referral
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserOut
from app.utils.audit import log_audit

router = APIRouter(prefix="/auth", tags=["Auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str
    referral_code: str | None = None


@router.post("/telegram", response_model=Token, summary="Telegram MiniApp authorization")
async def auth_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    try:
        data = verify_telegram_init_data(payload.init_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_data = json.loads(data.get("user", "{}"))
    telegram_id = int(user_data.get("id"))
    username = user_data.get("username")
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")

    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        is_new = False
        if not user:
            is_new = True
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referral_code=f"ref_{telegram_id}",
            )
            inviter = None
            if payload.referral_code:
                inviter = db.query(User).filter(User.referral_code == payload.referral_code).first()
                if inviter:
                    user.referred_by_id = inviter.id
                    user.trial_days = 7

            db.add(user)
            db.commit()
            db.refresh(user)

            if inviter:
                db.add(Referral(inviter_id=inviter.id, invitee_id=user.id))
                db.commit()

        token = create_access_token(str(user.id), user.is_admin)

        log_audit(db, user.id, "registration" if is_new else "login", {"username": username})
        if is_new:
            await send_admin_log(
                "registration",
                user.telegram_id,
                username,
                {
                    "referral": "yes" if user.referred_by_id else "no",
                    "trial_days": user.trial_days,
                },
            )

        return Token(access_token=token)
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@router.get("/me", response_model=UserOut, summary="Current user")
def get_me(user: User = Depends(get_current_user)):
    return user
