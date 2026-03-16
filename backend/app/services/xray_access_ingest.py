from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.connection_log import ConnectionLog
from app.models.ingestion_cursor import IngestionCursor
from app.models.user import User

USERNAME_RE = re.compile(r"\b(tg_\d{5,})\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
TS_STD_RE = re.compile(r"^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})")
TS_ISO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")


@dataclass
class ParsedEvent:
    panel_username: str
    telegram_id: int | None
    ip_address: str
    connected_at: datetime
    raw_event: str
    event_hash: str
    source_offset: int


def _parse_connected_at(line: str) -> datetime:
    m = TS_STD_RE.search(line)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y/%m/%d %H:%M:%S")
            return dt
        except ValueError:
            pass

    m = TS_ISO_RE.search(line)
    if m:
        raw = m.group(1).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            pass

    return datetime.utcnow()


def _extract_telegram_id(panel_username: str) -> int | None:
    if not panel_username.startswith("tg_"):
        return None
    raw = panel_username[3:]
    if not raw.isdigit():
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_line(line: str, source_offset: int) -> ParsedEvent | None:
    username_match = USERNAME_RE.search(line)
    ip_match = IPV4_RE.search(line)

    if not username_match or not ip_match:
        return None

    panel_username = username_match.group(1)
    telegram_id = _extract_telegram_id(panel_username)
    ip_address = ip_match.group(0)
    connected_at = _parse_connected_at(line)

    hash_src = f"{source_offset}|{line.rstrip()}"
    event_hash = hashlib.sha256(hash_src.encode("utf-8", errors="ignore")).hexdigest()

    return ParsedEvent(
        panel_username=panel_username,
        telegram_id=telegram_id,
        ip_address=ip_address,
        connected_at=connected_at,
        raw_event=line.rstrip(),
        event_hash=event_hash,
        source_offset=source_offset,
    )


def _get_or_create_cursor(db: Session, source_path: str) -> IngestionCursor:
    cursor = db.query(IngestionCursor).filter(IngestionCursor.cursor_key == settings.vpn_access_log_cursor_key).first()
    if cursor:
        return cursor

    cursor = IngestionCursor(
        cursor_key=settings.vpn_access_log_cursor_key,
        source_path=source_path,
        inode=None,
        offset=0,
    )
    db.add(cursor)
    db.commit()
    db.refresh(cursor)
    return cursor


def _safe_inode(path: str) -> str | None:
    try:
        st = os.stat(path)
        return str(getattr(st, "st_ino", "")) or None
    except FileNotFoundError:
        return None


def ingest_xray_access_log(db: Session) -> dict:
    source_path = settings.vpn_access_log_path
    result = {
        "processed": 0,
        "inserted": 0,
        "skipped": 0,
        "cursor_updated": False,
        "source_path": source_path,
        "error": None,
    }

    if not settings.vpn_access_log_enabled:
        result["error"] = "disabled"
        return result

    if not os.path.exists(source_path):
        result["error"] = "missing_file"
        return result

    cursor = _get_or_create_cursor(db, source_path)
    current_inode = _safe_inode(source_path)

    try:
        file_size = os.path.getsize(source_path)
    except OSError:
        result["error"] = "stat_error"
        return result

    offset = int(cursor.offset or 0)
    if offset > file_size:
        offset = 0

    if cursor.inode and current_inode and cursor.inode != current_inode:
        # Log rotated/recreated: restart from beginning of new file.
        offset = 0

    max_lines = max(int(settings.vpn_access_log_max_lines_per_run or 5000), 1)

    with open(source_path, "r", encoding="utf-8", errors="ignore") as fp:
        fp.seek(offset)

        lines_processed = 0
        while lines_processed < max_lines:
            line_offset = fp.tell()
            line = fp.readline()
            if not line:
                break
            lines_processed += 1
            result["processed"] += 1

            parsed = _parse_line(line, line_offset)
            if not parsed:
                result["skipped"] += 1
                continue

            exists = db.query(ConnectionLog.id).filter(ConnectionLog.event_hash == parsed.event_hash).first()
            if exists:
                result["skipped"] += 1
                continue

            user_id = None
            if parsed.telegram_id is not None:
                user = db.query(User.id).filter(User.telegram_id == parsed.telegram_id).first()
                if user:
                    user_id = user.id

            db.add(
                ConnectionLog(
                    user_id=user_id,
                    telegram_id=parsed.telegram_id,
                    panel_username=parsed.panel_username,
                    ip_address=parsed.ip_address,
                    connected_at=parsed.connected_at,
                    source_path=source_path,
                    source_offset=parsed.source_offset,
                    event_hash=parsed.event_hash,
                    raw_event=parsed.raw_event,
                )
            )
            result["inserted"] += 1

        new_offset = fp.tell()

    cursor.source_path = source_path
    cursor.inode = current_inode
    cursor.offset = new_offset
    result["cursor_updated"] = True

    db.commit()
    return result
