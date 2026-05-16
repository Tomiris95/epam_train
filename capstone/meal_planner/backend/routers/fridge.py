from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import models
from backend.schemas import FridgeItemCreate, FridgeItemOut
from backend.security import get_current_user

router = APIRouter(prefix="/fridge", tags=["fridge"])


def _check_family_owner(family_id: int, user: models.User, db: Session) -> models.Family:
    family = db.query(models.Family).filter(
        models.Family.id == family_id,
        models.Family.owner_id == user.id,
    ).first()
    if not family:
        raise HTTPException(404, "Family not found")
    return family


@router.get("/{family_id}", response_model=List[FridgeItemOut])
def get_fridge(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_family_owner(family_id, current_user, db)
    return db.query(models.FridgeItem).filter(models.FridgeItem.family_id == family_id).all()


@router.post("/{family_id}", response_model=FridgeItemOut)
def add_item(
    family_id: int,
    data: FridgeItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_family_owner(family_id, current_user, db)

    existing = db.query(models.FridgeItem).filter(
        models.FridgeItem.family_id == family_id,
        models.FridgeItem.ingredient == data.ingredient.lower().strip(),
    ).first()
    if existing:
        return existing

    item = models.FridgeItem(family_id=family_id, ingredient=data.ingredient.lower().strip())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{family_id}/bulk")
def add_items_bulk(
    family_id: int,
    ingredients: List[str],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_family_owner(family_id, current_user, db)

    added = []
    for ingredient in ingredients:
        name = ingredient.lower().strip()
        existing = db.query(models.FridgeItem).filter(
            models.FridgeItem.family_id == family_id,
            models.FridgeItem.ingredient == name,
        ).first()
        if not existing:
            db.add(models.FridgeItem(family_id=family_id, ingredient=name))
            added.append(name)

    db.commit()
    return {"added": added, "count": len(added)}


@router.delete("/{family_id}/{item_id}")
def remove_item(
    family_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_family_owner(family_id, current_user, db)
    item = db.query(models.FridgeItem).filter(
        models.FridgeItem.id == item_id,
        models.FridgeItem.family_id == family_id,
    ).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.delete("/{family_id}")
def clear_fridge(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_family_owner(family_id, current_user, db)
    db.query(models.FridgeItem).filter(models.FridgeItem.family_id == family_id).delete()
    db.commit()
    return {"ok": True}
