from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.schemas import ShoppingListOut
from backend.engine.shopping_engine import generate_shopping_list
from backend.engine.calorie_engine import compute_all_members_portions
from backend.security import get_current_user

router = APIRouter(prefix="/shopping", tags=["shopping"])


def _get_plan_or_404(plan_id: int, user: models.User, db: Session) -> models.MealPlan:
    plan = db.query(models.MealPlan).filter(models.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    family = db.query(models.Family).filter(
        models.Family.id == plan.family_id,
        models.Family.owner_id == user.id,
    ).first()
    if not family:
        raise HTTPException(403, "Access denied")
    return plan


@router.post("/{plan_id}/generate", response_model=ShoppingListOut)
def generate_shopping(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    family = db.query(models.Family).filter(models.Family.id == plan.family_id).first()

    recipe_map = {item.meal_type: item.recipe for item in plan.items}
    breakfast = recipe_map.get("breakfast")
    lunch = recipe_map.get("lunch")
    dinner = recipe_map.get("dinner")

    if not all([breakfast, lunch, dinner]):
        raise HTTPException(400, "Plan is incomplete — missing meal recipes")

    member_portions = compute_all_members_portions(family.members, breakfast, lunch, dinner)
    shopping_items = generate_shopping_list(
        recipes=[breakfast, lunch, dinner],
        member_count=len(family.members),
        member_portions=member_portions,
    )

    old = db.query(models.ShoppingList).filter(models.ShoppingList.meal_plan_id == plan_id).first()
    if old:
        db.delete(old)
        db.flush()

    sl = models.ShoppingList(meal_plan_id=plan_id)
    db.add(sl)
    db.flush()

    for item in shopping_items:
        db.add(models.ShoppingItem(
            shopping_list_id=sl.id,
            ingredient=item["ingredient"],
            grams_needed=item["grams_needed"],
        ))

    db.commit()
    db.refresh(sl)
    return sl


@router.get("/{plan_id}", response_model=ShoppingListOut)
def get_shopping_list(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_plan_or_404(plan_id, current_user, db)
    sl = db.query(models.ShoppingList).filter(models.ShoppingList.meal_plan_id == plan_id).first()
    if not sl:
        raise HTTPException(404, "Shopping list not found. Generate it first.")
    return sl
