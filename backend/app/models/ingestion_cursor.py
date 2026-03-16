from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionCursor(Base):
    __tablename__ = "ingestion_cursors"

    id: Mapped[int] = mapped_column(primary_key=True)
    cursor_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_path: Mapped[str] = mapped_column(String(512))
    inode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    offset: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
