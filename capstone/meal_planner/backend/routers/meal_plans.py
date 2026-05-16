import logging
import time
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.schemas import (
    GeneratePlanRequest, MealPlanOut, MealPlanDetailOut,
    MemberPortions, ReplaceMealRequest, ChatRequest, ChatResponse,
)
from backend.agents.preference_agent import PreferenceAgent
from backend.agents.recipe_agent import RecipeAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.conversational_agent import ConversationalAgent
from backend.rag import vector_store
from backend.security import get_current_user
from backend.limiter import limiter
from backend.content_filter import check_message
from backend.audit import log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])

# Module-level singletons: each agent opens an OpenAI client on init;
# creating them per-request would reconnect on every call.
_preference_agent = PreferenceAgent()
_recipe_agent = RecipeAgent()
_planner_agent = PlannerAgent()
_conversational_agent = ConversationalAgent()


def _ensure_index(db: Session):
    recipes = db.query(models.Recipe).all()
    if not vector_store.is_ready():
        vector_store.load_or_build_index(recipes)


def _get_family_or_404(family_id: int, user: models.User, db: Session) -> models.Family:
    family = db.query(models.Family).filter(
        models.Family.id == family_id,
        models.Family.owner_id == user.id,
    ).first()
    if not family:
        raise HTTPException(404, "Family not found")
    return family


def _get_plan_or_404(plan_id: int, user: models.User, db: Session) -> models.MealPlan:
    plan = db.query(models.MealPlan).filter(models.MealPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    _get_family_or_404(plan.family_id, user, db)
    return plan


def _build_detail(plan: models.MealPlan, member_portions: List[dict]) -> MealPlanDetailOut:
    portions_out = [
        MemberPortions(
            member_name=mp["member_name"],
            calorie_target=mp["calorie_target"],
            breakfast_grams=mp["breakfast_grams"],
            lunch_grams=mp["lunch_grams"],
            dinner_grams=mp["dinner_grams"],
            total_calories=mp["total_calories"],
            total_protein=mp.get("total_protein", 0.0),
            total_fat=mp.get("total_fat", 0.0),
            total_carbs=mp.get("total_carbs", 0.0),
        )
        for mp in member_portions
    ]
    return MealPlanDetailOut(plan=plan, member_portions=portions_out)


@router.post("/generate", response_model=MealPlanDetailOut)
@limiter.limit("10/minute")
def generate_meal_plan(
    request: Request,
    data: GeneratePlanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    family = _get_family_or_404(data.family_id, current_user, db)
    if not family.members:
        raise HTTPException(400, "Family has no members")

    _ensure_index(db)

    t0 = time.perf_counter()
    pref_result = _preference_agent.run(family.members)
    logger.info("PreferenceAgent: %.2fs", time.perf_counter() - t0)

    fridge_items = db.query(models.FridgeItem).filter(
        models.FridgeItem.family_id == data.family_id
    ).all()
    fridge_names = [fi.ingredient for fi in fridge_items]

    disliked_ids = [
        r.recipe_id for r in db.query(models.RecipeRating).filter(
            models.RecipeRating.user_id == current_user.id,
            models.RecipeRating.rating == -1,
        ).all()
    ]
    if disliked_ids:
        logger.info("Excluding %d disliked recipes from plan generation.", len(disliked_ids))

    # Soft-exclude recipes used in the last 3 approved plans for this family
    # to avoid serving the same meals day after day.
    recent_items = (
        db.query(models.MealPlanItem)
        .join(models.MealPlan, models.MealPlanItem.meal_plan_id == models.MealPlan.id)
        .filter(
            models.MealPlan.family_id == data.family_id,
            models.MealPlan.approved == True,
        )
        .order_by(models.MealPlan.id.desc())
        .limit(9)   # 3 plans × 3 meals
        .all()
    )
    recent_ids = list({item.recipe_id for item in recent_items} - set(disliked_ids))
    if recent_ids:
        logger.info("Soft-excluding %d recently served recipes for variety.", len(recent_ids))

    t1 = time.perf_counter()
    plan_result = _planner_agent.run(
        db=db,
        preference_result=pref_result,
        members=family.members,
        fridge_items=fridge_names,
        disliked_ids=disliked_ids + recent_ids,
    )
    logger.info("PlannerAgent: %.2fs", time.perf_counter() - t1)
    logger.info("generate_meal_plan total: %.2fs", time.perf_counter() - t0)

    plan_date = data.date if data.date != "today" else str(date.today())
    plan = models.MealPlan(family_id=data.family_id, date=plan_date, approved=False)
    db.add(plan)
    db.flush()  # assigns plan.id without committing, so plan + items are one atomic commit

    for meal_type in ["breakfast", "lunch", "dinner"]:
        recipe = plan_result[meal_type]
        db.add(models.MealPlanItem(
            meal_plan_id=plan.id,
            meal_type=meal_type,
            recipe_id=recipe.id,
        ))

    db.commit()
    db.refresh(plan)

    log_event(
        db, "plan_generated",
        user_id=current_user.id,
        family_id=data.family_id,
        plan_id=plan.id,
        retries=plan_result["retries"],
        breakfast=plan_result["breakfast"].name,
        lunch=plan_result["lunch"].name,
        dinner=plan_result["dinner"].name,
    )

    return _build_detail(plan, plan_result["member_portions"])


@router.get("/family/{family_id}", response_model=List[MealPlanOut])
def list_plans(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_family_or_404(family_id, current_user, db)
    return (
        db.query(models.MealPlan)
        .filter(models.MealPlan.family_id == family_id)
        .order_by(models.MealPlan.id.desc())
        .all()
    )


@router.get("/{plan_id}", response_model=MealPlanOut)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_plan_or_404(plan_id, current_user, db)


@router.post("/{plan_id}/replace", response_model=MealPlanDetailOut)
@limiter.limit("10/minute")
def replace_meal(
    request: Request,
    plan_id: int,
    data: ReplaceMealRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    if plan.approved:
        raise HTTPException(400, "Cannot modify an approved plan")

    family = db.query(models.Family).filter(models.Family.id == plan.family_id).first()
    _ensure_index(db)
    pref_result = _preference_agent.run(family.members)

    disliked_ids = [
        r.recipe_id for r in db.query(models.RecipeRating).filter(
            models.RecipeRating.user_id == current_user.id,
            models.RecipeRating.rating == -1,
        ).all()
    ]

    items = {item.meal_type: item for item in plan.items}
    other_recipes = {mt: item.recipe for mt, item in items.items() if mt != data.meal_type}

    result = _planner_agent.replace_meal(
        db=db,
        preference_result=pref_result,
        members=family.members,
        meal_type=data.meal_type,
        current_recipe_id=data.recipe_id,
        other_recipes=other_recipes,
        disliked_ids=disliked_ids,
    )

    meal_item = items.get(data.meal_type)
    if meal_item:
        meal_item.recipe_id = result["recipe"].id
        db.commit()
        db.refresh(plan)

    log_event(
        db, "meal_replaced",
        user_id=current_user.id,
        plan_id=plan_id,
        meal_type=data.meal_type,
        new_recipe=result["recipe"].name,
    )

    return _build_detail(plan, result["member_portions"])


@router.post("/{plan_id}/approve", response_model=MealPlanOut)
def approve_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    plan.approved = True
    db.commit()
    db.refresh(plan)
    log_event(db, "plan_approved", user_id=current_user.id, plan_id=plan_id)
    return plan


@router.post("/{plan_id}/unapprove", response_model=MealPlanOut)
def unapprove_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    plan.approved = False
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat_with_plan(
    request: Request,
    plan_id: int,
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    if plan.approved:
        raise HTTPException(400, "Cannot modify an approved plan")

    is_safe, reason = check_message(data.message)
    if not is_safe:
        raise HTTPException(400, reason)

    _ensure_index(db)

    disliked_ids = [
        r.recipe_id for r in db.query(models.RecipeRating).filter(
            models.RecipeRating.user_id == current_user.id,
            models.RecipeRating.rating == -1,
        ).all()
    ]

    t0 = time.perf_counter()
    result = _conversational_agent.run(
        db=db,
        plan=plan,
        user_message=data.message,
        chat_history=data.history,
        disliked_ids=disliked_ids,
    )
    logger.info("ConversationalAgent total: %.2fs", time.perf_counter() - t0)

    updated_plan_out = None
    if result["updated_plan"]:
        db.refresh(plan)
        updated_plan_out = _build_detail(plan, result["updated_plan"]["member_portions"])

    log_event(
        db, "chat_message",
        user_id=current_user.id,
        plan_id=plan_id,
        plan_updated=result["updated_plan"] is not None,
        total_tokens=result.get("total_tokens", 0),
        estimated_cost_usd=result.get("estimated_cost_usd", 0.0),
    )

    return ChatResponse(response=result["response"], updated_plan=updated_plan_out)


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _get_plan_or_404(plan_id, current_user, db)
    log_event(db, "plan_deleted", user_id=current_user.id, plan_id=plan_id)
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.post("/cleanup")
def cleanup_old_plans(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete unapproved meal plans older than N days for the current user's families."""
    cutoff = str(date.today() - timedelta(days=days))
    old_plans = (
        db.query(models.MealPlan)
        .join(models.Family, models.MealPlan.family_id == models.Family.id)
        .filter(
            models.Family.owner_id == current_user.id,
            models.MealPlan.approved == False,
            models.MealPlan.date < cutoff,
        )
        .all()
    )
    count = len(old_plans)
    for plan in old_plans:
        db.delete(plan)
    db.commit()
    log_event(db, "cleanup", user_id=current_user.id, deleted_count=count, cutoff_date=cutoff)
    logger.info("Data retention cleanup: deleted %d unapproved plans older than %s", count, cutoff)
    return {"deleted": count, "cutoff_date": cutoff}
