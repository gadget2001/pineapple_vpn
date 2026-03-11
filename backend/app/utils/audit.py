from app.models.audit_log import AuditLog


def log_audit(db, user_id: int | None, action: str, details: dict | None = None):
    entry = AuditLog(user_id=user_id, action=action, details=details or {})
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
