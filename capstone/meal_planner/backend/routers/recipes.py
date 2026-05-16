from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend import models
from backend.security import get_current_user
from backend.schemas import RatingCreate

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.post("/{recipe_id}/rate")
def rate_recipe(
    recipe_id: int,
    data: RatingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first():
        raise HTTPException(404, "Recipe not found")

    existing = db.query(models.RecipeRating).filter(
        models.RecipeRating.user_id == current_user.id,
        models.RecipeRating.recipe_id == recipe_id,
    ).first()

    if data.rating is None:
        if existing:
            db.delete(existing)
            db.commit()
        return {"recipe_id": recipe_id, "rating": None}

    if existing:
        existing.rating = data.rating
    else:
        db.add(models.RecipeRating(
            user_id=current_user.id,
            recipe_id=recipe_id,
            rating=data.rating,
        ))
    db.commit()
    return {"recipe_id": recipe_id, "rating": data.rating}


@router.get("/{recipe_id}/my-rating")
def get_my_rating(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.RecipeRating).filter(
        models.RecipeRating.user_id == current_user.id,
        models.RecipeRating.recipe_id == recipe_id,
    ).first()
    return {"recipe_id": recipe_id, "rating": existing.rating if existing else None}
