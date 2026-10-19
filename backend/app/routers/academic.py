from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_user, resolve_access_user
from app.models.entities import CourseMaterial, Period, ScheduleItem, Term, User
from app.schemas import MaterialOut, PeriodOut, ScheduleItemOut, TermOut, UserOut

router = APIRouter(prefix="/academic", tags=["教务"])


@router.get("/term", response_model=TermOut | None)
def current_term(db: Session = Depends(get_db), _me: User = Depends(get_current_user)):
    return db.scalar(select(Term).where(Term.is_current.is_(True)))


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(db: Session = Depends(get_db), _me: User = Depends(get_current_user)):
    """课表作息节次定义（前端课表格子数据来源）。"""
    return list(db.scalars(select(Period).order_by(Period.sort_order, Period.slot)))


@router.get("/schedule/today", response_model=list[ScheduleItemOut])
def today_schedule(
    username: str | None = Query(default=None),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    user = resolve_access_user(db, me, username)
    return list(
        db.scalars(
            select(ScheduleItem)
            .where(ScheduleItem.user_id == user.id, ScheduleItem.day == 1)
            .order_by(ScheduleItem.slot)
        )
    )


@router.get("/schedule/weekly", response_model=list[ScheduleItemOut])
def weekly_schedule(
    username: str | None = Query(default=None),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    user = resolve_access_user(db, me, username)
    return list(
        db.scalars(
            select(ScheduleItem)
            .where(ScheduleItem.user_id == user.id)
            .order_by(ScheduleItem.day, ScheduleItem.slot)
        )
    )


@router.get("/materials", response_model=list[MaterialOut])
def materials(
    course: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _me: User = Depends(get_current_user),
):
    stmt = select(CourseMaterial).order_by(CourseMaterial.id)
    if course:
        stmt = stmt.where(CourseMaterial.course.like(f"%{course[:4]}%"))
    return list(db.scalars(stmt))


@router.get("/users", response_model=list[UserOut])
def user_list(db: Session = Depends(get_db), _me: User = Depends(get_admin_user)):
    """用户列表：仅管理员可访问（普通用户不应枚举他人账号）。"""
    return list(db.scalars(select(User)))


@router.post("/rag/sync")
def rag_sync(db: Session = Depends(get_db), _me: User = Depends(get_admin_user)):
    from app.services import rag_service

    n = rag_service.sync_index(db)
    return {"ok": True, "indexed": n}
