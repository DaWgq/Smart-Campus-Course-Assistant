from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------- Auth / User ----------------
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(default="")
    major: str = Field(default="")
    grade: str = Field(default="")


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    major: str
    grade: str
    role: str = "student"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------- Term ----------------
class TermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    is_current: bool


# ---------------- Period ----------------
class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot: int
    name: str
    time_range: str
    day_label: str
    weekday: int
    sort_order: int


# ---------------- Schedule ----------------
class ScheduleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day: int
    slot: int
    time_range: str
    course_name: str
    teacher: str
    room: str
    weeks: str
    color: str
    material_key: str


# ---------------- Materials ----------------
class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course: str
    code: str
    docs: str
    focus: str


# ---------------- Study Plan ----------------
class StudyPlanCreate(BaseModel):
    title: str
    plan_type: str = "复习计划"
    status: str = "进行中"
    items: list[str] = Field(default_factory=list)
    raw_draft: str = ""


class StudyPlanUpdate(BaseModel):
    title: str | None = None
    plan_type: str | None = None
    status: str | None = None
    items: list[str] | None = None


class StudyPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    plan_type: str
    status: str
    items: list[str]
    created_at: datetime


# ---------------- Chat ----------------
class ChatSend(BaseModel):
    message: str
    username: str | None = None
    session_id: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: str | None = None
