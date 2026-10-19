from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    major: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    grade: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="student")  # student | admin
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    schedules: Mapped[list["ScheduleItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[list["StudyPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Term(Base):
    """当前学年学期信息。"""

    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Period(Base):
    """作息节次定义（课表格子数据）。"""

    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slot: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    time_range: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    day_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    weekday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0=周一 ... 4=周五
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ScheduleItem(Base):
    __tablename__ = "schedule_items"
    __table_args__ = (UniqueConstraint("user_id", "day", "slot", name="uq_schedule_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5 周一..周五
    slot: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5 节次
    time_range: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    course_name: Mapped[str] = mapped_column(String(128), nullable=False)
    teacher: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    room: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    weeks: Mapped[str] = mapped_column(String(64), nullable=False, default="1-16周")
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="blue")
    material_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    user: Mapped[User] = relationship(back_populates="schedules")


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    docs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    focus: Mapped[str] = mapped_column(Text, nullable=False, default="")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False, default="复习计划")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="进行中")
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_draft: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="plans")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="新的对话")
    history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
