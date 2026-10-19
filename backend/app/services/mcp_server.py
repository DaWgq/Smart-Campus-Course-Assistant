"""FastMCP 工具服务：课表查询 / 课程资料检索 / 学习计划落库。"""
from __future__ import annotations

import json

from fastmcp import FastMCP
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import CourseMaterial, ScheduleItem, StudyPlan, User

mcp = FastMCP("campus-course-assistant")

WEEKDAYS = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五"}

# LangGraph 直调工具表：函数名 -> 可调用对象。
# 显式维护，避免依赖 FastMCP 内部实现，保证在任何上下文（含事件循环）中均可用。
_TOOL_REGISTRY: dict = {}


def _tool(fn):
    """同时注册到 FastMCP（对外暴露）与本地注册表（LangGraph 直调）。"""
    _TOOL_REGISTRY[fn.__name__] = fn
    return mcp.tool(fn)


def _get_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


@_tool
def get_today_schedule(username: str) -> str:
    """查询指定学生今天(默认周一)的课程表，返回 JSON。"""
    db: Session = SessionLocal()
    try:
        user = _get_user(db, username)
        if not user:
            return json.dumps({"ok": False, "message": f"未找到用户 {username}"}, ensure_ascii=False)
        items = db.scalars(
            select(ScheduleItem).where(ScheduleItem.user_id == user.id).order_by(ScheduleItem.slot)
        ).all()
        today = [i for i in items if i.day == 1]
        return json.dumps(
            {
                "ok": True,
                "username": user.username,
                "nickname": user.nickname,
                "day": WEEKDAYS[1],
                "count": len(today),
                "courses": [
                    {
                        "slot": i.slot,
                        "name": i.course_name,
                        "teacher": i.teacher,
                        "room": i.room,
                        "time": i.time_range,
                        "weeks": i.weeks,
                    }
                    for i in today
                ],
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def get_weekly_schedule(username: str) -> str:
    """查询指定学生一周全部课程，返回 JSON。"""
    db: Session = SessionLocal()
    try:
        user = _get_user(db, username)
        if not user:
            return json.dumps({"ok": False, "message": f"未找到用户 {username}"}, ensure_ascii=False)
        items = db.scalars(
            select(ScheduleItem)
            .where(ScheduleItem.user_id == user.id)
            .order_by(ScheduleItem.day, ScheduleItem.slot)
        ).all()
        return json.dumps(
            {
                "ok": True,
                "username": user.username,
                "total": len(items),
                "courses": [
                    {
                        "day": i.day,
                        "weekday": WEEKDAYS.get(i.day, str(i.day)),
                        "slot": i.slot,
                        "name": i.course_name,
                        "teacher": i.teacher,
                        "room": i.room,
                        "time": i.time_range,
                    }
                    for i in items
                ],
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def search_course_materials(course: str, question: str = "") -> str:
    """按课程名/问题在 Chroma RAG 资料库中检索，返回 JSON。"""
    from app.services import rag_service

    db: Session = SessionLocal()
    try:
        mats = db.scalars(select(CourseMaterial).order_by(CourseMaterial.id)).all()
        m = None
        key = (course or "").strip()
        for cand in mats:
            if key and (key == cand.course or key in cand.course or cand.course in key):
                m = cand
                break
        if m is None and key:
            for cand in mats:
                if key[:2] and key[:2] in cand.course:
                    m = cand
                    break
        chunks = rag_service.search(f"{course} {question}".strip(), top_k=4)
        payload = {
            "ok": True,
            "matched": m is not None,
            "requested": course,
            "course": m.course if m else course,
            "code": m.code if m else "",
            "docs": m.docs if m else "",
            "focus": m.focus if m else "",
            "chunks": chunks,
            "available_courses": [x.course for x in mats],
        }
        return json.dumps(payload, ensure_ascii=False)
    finally:
        db.close()


@_tool
def list_course_materials() -> str:
    """列出全部已接入 RAG 的课程资料索引。"""
    db: Session = SessionLocal()
    try:
        mats = db.scalars(select(CourseMaterial).order_by(CourseMaterial.id)).all()
        return json.dumps(
            {
                "ok": True,
                "courses": [{"course": m.course, "code": m.code, "docs": m.docs} for m in mats],
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def save_study_plan(
    username: str,
    title: str,
    plan_type: str = "复习计划",
    items: list[str] | None = None,
) -> str:
    """将学习计划保存到用户计划库，返回 JSON。"""
    db: Session = SessionLocal()
    try:
        user = _get_user(db, username)
        if not user:
            return json.dumps({"ok": False, "message": f"未找到用户 {username}"}, ensure_ascii=False)
        plan = StudyPlan(
            user_id=user.id,
            title=title,
            plan_type=plan_type or "复习计划",
            status="进行中",
            items=items or [],
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return json.dumps(
            {
                "ok": True,
                "plan_id": plan.id,
                "title": plan.title,
                "item_count": len(plan.items),
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def list_study_plans(username: str) -> str:
    """列出指定用户已保存的学习计划。"""
    db: Session = SessionLocal()
    try:
        user = _get_user(db, username)
        if not user:
            return json.dumps({"ok": False, "message": f"未找到用户 {username}"}, ensure_ascii=False)
        plans = db.scalars(
            select(StudyPlan).where(StudyPlan.user_id == user.id).order_by(StudyPlan.id.desc())
        ).all()
        return json.dumps(
            {
                "ok": True,
                "total": len(plans),
                "plans": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "plan_type": p.plan_type,
                        "status": p.status,
                        "items": p.items,
                    }
                    for p in plans
                ],
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def delete_study_plan(plan_id: int) -> str:
    """删除指定学习计划。"""
    db: Session = SessionLocal()
    try:
        db.execute(delete(StudyPlan).where(StudyPlan.id == plan_id))
        db.commit()
        return json.dumps({"ok": True, "plan_id": plan_id}, ensure_ascii=False)
    finally:
        db.close()


@_tool
def list_users() -> str:
    """列出系统内可查询的学生账号。"""
    db: Session = SessionLocal()
    try:
        users = db.scalars(select(User)).all()
        return json.dumps(
            {
                "ok": True,
                "users": [
                    {
                        "username": u.username,
                        "nickname": u.nickname,
                        "major": u.major,
                        "grade": u.grade,
                    }
                    for u in users
                ],
            },
            ensure_ascii=False,
        )
    finally:
        db.close()


@_tool
def create_user(
    username: str,
    password: str = "123456",
    nickname: str = "",
    major: str = "",
    grade: str = "",
) -> str:
    """创建学生账号。"""
    db: Session = SessionLocal()
    try:
        if _get_user(db, username):
            return json.dumps({"ok": False, "message": f"用户 {username} 已存在"}, ensure_ascii=False)
        user = User(
            username=username,
            hashed_password=hash_password(password),
            nickname=nickname or username,
            major=major,
            grade=grade,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return json.dumps({"ok": True, "user_id": user.id, "username": user.username}, ensure_ascii=False)
    finally:
        db.close()


def build_tool_map() -> dict:
    """构建 LangGraph 可直接调用的工具函数表（纯同步，无 asyncio 依赖）。

    早期实现依赖 FastMCP 内部结构 + asyncio.run() 获取工具，
    在 FastAPI 的事件循环上下文中 asyncio.run 会抛 RuntimeError，
    导致 TOOLS 静默为空（所有工具报"不存在"）。这里改为显式注册表，
    与 FastMCP 版本无关，且始终同步可用。
    """
    return dict(_TOOL_REGISTRY)
