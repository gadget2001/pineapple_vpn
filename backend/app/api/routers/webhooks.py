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


@router.post(
    "/connection",
    summary="Лог подключения из VPN-панели",
    description="Системный webhook для записи сетевых логов (Telegram ID, IP, время) от панели VPN.",
)
def connection_log(
    payload: ConnectionEvent,
    x_panel_token: str = Header(None),
    db: Session = Depends(get_db),
):
    if x_panel_token != settings.panel_token:
        raise HTTPException(status_code=403, detail="Неверный токен панели.")

    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    raw = f"webhook telegram_id={payload.telegram_id} ip={payload.ip_address}"

    log = ConnectionLog(
        user_id=user.id,
        telegram_id=user.telegram_id,
        panel_username=f"tg_{user.telegram_id}",
        ip_address=payload.ip_address,
        raw_event=raw,
        source_path="webhook",
        source_offset=0,
        event_hash=None,
    )
    db.add(log)
    db.commit()

    return {"status": "ok"}
