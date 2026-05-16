"""
Deletes all Spoonacular recipes (no 'stol5' tag) and any meal plans
that referenced them, then prints how many were removed.

Run before re-seeding: python clear_spoonacular.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend import models

db = SessionLocal()
try:
    stol5_ids = {
        r.recipe_id
        for r in db.query(models.RecipeTag).filter(models.RecipeTag.tag == "stol5").all()
    }
    spoonacular = db.query(models.Recipe).filter(~models.Recipe.id.in_(stol5_ids)).all()

    if not spoonacular:
        print("No Spoonacular recipes found — nothing to delete.")
    else:
        spoon_ids = {r.id for r in spoonacular}

        # Find and delete meal plans that reference any Spoonacular recipe
        affected_items = (
            db.query(models.MealPlanItem)
            .filter(models.MealPlanItem.recipe_id.in_(spoon_ids))
            .all()
        )
        affected_plan_ids = {item.meal_plan_id for item in affected_items}
        plans_deleted = 0
        for plan_id in affected_plan_ids:
            plan = db.query(models.MealPlan).filter(models.MealPlan.id == plan_id).first()
            if plan:
                db.delete(plan)
                plans_deleted += 1

        # Delete the Spoonacular recipes (cascade removes their items/tags)
        for r in spoonacular:
            db.delete(r)

        db.commit()
        print(f"Deleted {len(spoonacular)} Spoonacular recipes.")
        print(f"Deleted {plans_deleted} meal plans that referenced them.")
        print("Now re-run: python spoonacular_seed.py --api-key YOUR_KEY")
finally:
    db.close()
