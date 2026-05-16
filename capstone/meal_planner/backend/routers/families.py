from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import models
from backend.schemas import FamilyCreate, FamilyOut, FamilyMemberCreate, FamilyMemberOut, FamilyMemberUpdate
from backend.security import get_current_user

router = APIRouter(prefix="/families", tags=["families"])


def _get_family_or_404(family_id: int, user: models.User, db: Session) -> models.Family:
    family = db.query(models.Family).filter(
        models.Family.id == family_id,
        models.Family.owner_id == user.id,
    ).first()
    if not family:
        raise HTTPException(404, "Family not found")
    return family


@router.post("/", response_model=FamilyOut)
def create_family(
    data: FamilyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    family = models.Family(name=data.name, owner_id=current_user.id)
    db.add(family)
    db.flush()

    for member_data in data.members:
        member = models.FamilyMember(
            family_id=family.id,
            name=member_data.name,
            age=member_data.age,
            calorie_target=member_data.calorie_target,
        )
        db.add(member)
        db.flush()
        for tag in member_data.diet_tags:
            db.add(models.MemberDietTag(
                member_id=member.id,
                tag=tag.tag,
                is_forbidden=tag.is_forbidden,
            ))

    db.commit()
    db.refresh(family)
    return family


@router.get("/", response_model=List[FamilyOut])
def list_families(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Family).filter(models.Family.owner_id == current_user.id).all()


@router.get("/{family_id}", response_model=FamilyOut)
def get_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_family_or_404(family_id, current_user, db)


@router.delete("/{family_id}")
def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    family = _get_family_or_404(family_id, current_user, db)
    db.delete(family)
    db.commit()
    return {"ok": True}


@router.post("/{family_id}/members", response_model=FamilyMemberOut)
def add_member(
    family_id: int,
    data: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    family = _get_family_or_404(family_id, current_user, db)

    member = models.FamilyMember(
        family_id=family.id,
        name=data.name,
        age=data.age,
        calorie_target=data.calorie_target,
    )
    db.add(member)
    db.flush()
    for tag in data.diet_tags:
        db.add(models.MemberDietTag(
            member_id=member.id,
            tag=tag.tag,
            is_forbidden=tag.is_forbidden,
        ))
    db.commit()
    db.refresh(member)
    return member


@router.put("/{family_id}/members/{member_id}", response_model=FamilyMemberOut)
def update_member(
    family_id: int,
    member_id: int,
    data: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_family_or_404(family_id, current_user, db)
    member = db.query(models.FamilyMember).filter(
        models.FamilyMember.id == member_id,
        models.FamilyMember.family_id == family_id,
    ).first()
    if not member:
        raise HTTPException(404, "Member not found")

    member.age = data.age
    member.calorie_target = data.calorie_target

    db.query(models.MemberDietTag).filter(models.MemberDietTag.member_id == member_id).delete()
    for tag in data.diet_tags:
        db.add(models.MemberDietTag(member_id=member.id, tag=tag.tag, is_forbidden=tag.is_forbidden))

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{family_id}/members/{member_id}")
def remove_member(
    family_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_family_or_404(family_id, current_user, db)
    member = db.query(models.FamilyMember).filter(
        models.FamilyMember.id == member_id,
        models.FamilyMember.family_id == family_id,
    ).first()
    if not member:
        raise HTTPException(404, "Member not found")
    db.delete(member)
    db.commit()
    return {"ok": True}
