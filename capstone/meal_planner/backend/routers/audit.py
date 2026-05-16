import json
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend import models
from backend.security import get_current_user
from backend.audit import log_event

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return audit log entries for the current user, newest first."""
    q = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == current_user.id)
        .order_by(models.AuditLog.id.desc())
    )
    if action:
        q = q.filter(models.AuditLog.action == action)

    logs = q.limit(limit).all()
    return [
        {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "action": entry.action,
            "family_id": entry.family_id,
            "plan_id": entry.plan_id,
            "details": json.loads(entry.details) if entry.details else None,
        }
        for entry in logs
    ]


@router.get("/stats")
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Aggregated usage statistics derived from the audit log."""
    base = db.query(models.AuditLog).filter(models.AuditLog.user_id == current_user.id)

    tracked_actions = [
        "plan_generated", "plan_approved", "plan_deleted",
        "meal_replaced", "chat_message", "login", "register",
        "cleanup", "chat_response_rated",
    ]
    by_action = {action: base.filter(models.AuditLog.action == action).count()
                 for action in tracked_actions}

    chat_rows = base.filter(models.AuditLog.action == "chat_message").all()
    chat_total = len(chat_rows)
    chat_updated = 0
    total_tokens = 0
    total_cost = 0.0
    for row in chat_rows:
        if row.details:
            d = json.loads(row.details)
            if d.get("plan_updated"):
                chat_updated += 1
            total_tokens += d.get("total_tokens", 0)
            total_cost   += d.get("estimated_cost_usd", 0.0)

    success_rate = round(chat_updated / chat_total * 100, 1) if chat_total else None

    return {
        "total_events": base.count(),
        "by_action": by_action,
        "chat_replacement_success_rate_pct": success_rate,
        "openai": {
            "total_tokens_used": total_tokens,
            "estimated_total_cost_usd": round(total_cost, 4),
        },
    }


class ChatRatingRequest(BaseModel):
    rating: int          # 1 = helpful, -1 = not helpful
    response_preview: str = ""   # first 100 chars of the AI response


@router.post("/rate-chat")
def rate_chat_response(
    data: ChatRatingRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Store user feedback on a conversational agent response."""
    if data.rating not in (1, -1):
        from fastapi import HTTPException
        raise HTTPException(400, "Rating must be 1 or -1")
    log_event(
        db, "chat_response_rated",
        user_id=current_user.id,
        rating=data.rating,
        response_preview=data.response_preview[:100],
    )
    return {"ok": True}
