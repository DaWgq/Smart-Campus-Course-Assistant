from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, resolve_access_user
from app.models.entities import StudyPlan, User
from app.schemas import StudyPlanCreate, StudyPlanOut, StudyPlanUpdate

router = APIRouter(prefix="/plans", tags=["学习计划"])


@router.get("", response_model=list[StudyPlanOut])
def list_plans(
    username: str | None = None,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """学习计划列表：普通用户仅能查看自己的，管理员可查看指定用户。"""
    target = resolve_access_user(db, me, username)
    return list(
        db.scalars(select(StudyPlan).where(StudyPlan.user_id == target.id).order_by(StudyPlan.id.desc()))
    )


@router.post("", response_model=StudyPlanOut)
def create_plan(
    payload: StudyPlanCreate, db: Session = Depends(get_db), me: User = Depends(get_current_user)
):
    plan = StudyPlan(
        user_id=me.id,
        title=payload.title,
        plan_type=payload.plan_type,
        status=payload.status,
        items=payload.items,
        raw_draft=payload.raw_draft,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/{plan_id}", response_model=StudyPlanOut)
def update_plan(
    plan_id: int, payload: StudyPlanUpdate, db: Session = Depends(get_db), me: User = Depends(get_current_user)
):
    plan = db.get(StudyPlan, plan_id)
    if not plan or plan.user_id != me.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "计划不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    plan = db.get(StudyPlan, plan_id)
    if not plan or plan.user_id != me.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "计划不存在")
    db.delete(plan)
    db.commit()
    return {"ok": True, "plan_id": plan_id}
