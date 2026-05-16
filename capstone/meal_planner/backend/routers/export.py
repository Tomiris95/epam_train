"""
GET /export  — returns all data belonging to the authenticated user as JSON.
Covers the GDPR/compliance "right to data portability" requirement.
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.security import get_current_user

router = APIRouter(prefix="/export", tags=["export"])


@router.get("")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export all user data as structured JSON (data portability)."""

    families = db.query(models.Family).filter(models.Family.owner_id == current_user.id).all()
    family_ids = [f.id for f in families]

    plans = (
        db.query(models.MealPlan)
        .filter(models.MealPlan.family_id.in_(family_ids))
        .all()
    ) if family_ids else []

    ratings = db.query(models.RecipeRating).filter(
        models.RecipeRating.user_id == current_user.id
    ).all()

    audit_logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == current_user.id)
        .order_by(models.AuditLog.id.asc())
        .all()
    )

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
        "families": [
            {
                "id": f.id,
                "name": f.name,
                "members": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "age": m.age,
                        "calorie_target": m.calorie_target,
                        "diet_tags": [{"tag": t.tag, "is_forbidden": t.is_forbidden} for t in m.diet_tags],
                    }
                    for m in f.members
                ],
                "fridge_items": [fi.ingredient for fi in f.fridge_items],
            }
            for f in families
        ],
        "meal_plans": [
            {
                "id": p.id,
                "family_id": p.family_id,
                "date": p.date,
                "approved": p.approved,
                "meals": [
                    {
                        "meal_type": item.meal_type,
                        "recipe_name": item.recipe.name if item.recipe else None,
                    }
                    for item in p.items
                ],
            }
            for p in plans
        ],
        "recipe_ratings": [
            {"recipe_id": r.recipe_id, "rating": r.rating}
            for r in ratings
        ],
        "audit_log": [
            {
                "timestamp": entry.timestamp,
                "action": entry.action,
                "plan_id": entry.plan_id,
                "details": json.loads(entry.details) if entry.details else None,
            }
            for entry in audit_logs
        ],
    }

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="meal_planner_export_{current_user.username}.json"'},
    )
