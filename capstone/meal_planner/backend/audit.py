import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend import models

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    family_id: Optional[int] = None,
    plan_id: Optional[int] = None,
    **details,
) -> None:
    try:
        entry = models.AuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            action=action,
            family_id=family_id,
            plan_id=plan_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
        )
        db.add(entry)
        db.commit()
        logger.info("AUDIT | action=%s user_id=%s plan_id=%s", action, user_id, plan_id)
    except Exception as e:
        logger.error("Failed to write audit log: %s", e)
