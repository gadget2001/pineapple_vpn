from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.connection_log import ConnectionLog
from app.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class ConnectionEvent(BaseModel):
    telegram_id: int
    ip_address: str


@router.post("/connection")
def connection_log(
    payload: ConnectionEvent,
    x_panel_token: str = Header(None),
    db: Session = Depends(get_db),
):
    if x_panel_token != settings.panel_token:
        raise HTTPException(status_code=403, detail="Invalid token")

    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log = ConnectionLog(user_id=user.id, ip_address=payload.ip_address)
    db.add(log)
    db.commit()
    return {"status": "ok"}
